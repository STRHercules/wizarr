from __future__ import annotations

"""Romm media‐server client.

This minimal implementation lets Wizarr recognise RomM as a media‐server
backend so that an admin can store RomM connection credentials, scan the
list of *platforms* (treated as "libraries"), and present basic read‐only
user information in the UI.

NOTE – RomM exposes a comprehensive HTTP API that is documented via
OpenAPI (see /api/docs on any RomM instance).  To keep the initial
integration small we only implement the endpoints that Wizarr currently
needs:

    * GET /api/platforms  –>  list of platforms (= libraries)
    * GET /api/users      –>  list all users (admin only)


"""

import logging
import datetime
import re
from typing import Any, Dict, List

from sqlalchemy import or_

from app.extensions import db
from app.models import User, Invitation
from .client_base import RestApiMixin, register_media_client
from app.services.invites import is_invite_valid, mark_server_used
from app.services.notifications import notify
import requests  # local import to avoid top-level dependency chatter

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

# Simple e-mail validation (same pattern as other clients)
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")

@register_media_client("romm")
class RommClient(RestApiMixin):
    """Very small wrapper around the RomM REST API."""

    API_PREFIX = "/api"

    def __init__(self, *args, **kwargs):
        # Defaults for historical callers
        kwargs.setdefault("url_key", "server_url")
        kwargs.setdefault("token_key", "api_key")
        super().__init__(*args, **kwargs)

    def _headers(self) -> Dict[str, str]:  # type: ignore[override]
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Basic {self.token}"
        return headers

    # ------------------------------------------------------------------
    # Wizarr API – libraries
    # ------------------------------------------------------------------

    def libraries(self) -> Dict[str, str]:
        """Return mapping ``platform_id`` → ``display_name``.

        RomM's *platforms* endpoint returns JSON like::

            [ {"id": "nes", "name": "Nintendo Entertainment System", ...}, ... ]
        """
        try:
            r = self.get(f"{self.API_PREFIX}/platforms")
            data: List[Dict[str, Any]] = r.json()
            return {p["id"]: p.get("name", p["id"]) for p in data}
        except Exception as exc:  # noqa: BLE001
            logging.warning("ROMM: failed to fetch platforms – %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Wizarr API – users (read-only)
    # ------------------------------------------------------------------

    def list_users(self) -> List[User]:
        """Sync RomM users into local DB (read-only).

        Requires the supplied API token to belong to a RomM *admin* user as
        `/api/users` is admin-only.
        """
        # RomM supports pagination via ?skip= & take= parameters.  We fetch in
        # chunks of *take*=100 until the returned set is smaller than the
        # requested size, indicating we've reached the end.

        remote_users: List[Dict[str, Any]] = []
        skip, take = 0, 100
        try:
            while True:
                r = self.get(f"{self.API_PREFIX}/users", params={"skip": skip, "take": take})
                batch: List[Dict[str, Any]] = r.json()
                # Some RomM versions wrap the list in {"items": [...]} – handle both.
                if isinstance(batch, dict) and "items" in batch:
                    batch = batch["items"]  # type: ignore[assignment]

                if not isinstance(batch, list):
                    logging.warning("ROMM: unexpected /users payload: %s", batch)
                    break

                remote_users.extend(batch)

                if len(batch) < take:
                    break  # reached final page
                skip += take
        except Exception as exc:  # noqa: BLE001
            logging.warning("ROMM: failed to list users – %s", exc, exc_info=True)
            return []

        remote_by_id = {str(u.get("id") or u["username"]): u for u in remote_users}

        # 1) upsert basic user rows so Wizarr UI has something to show
        for romm_id, ru in remote_by_id.items():
            db_row: User | None = (
                User.query.filter_by(token=romm_id, server_id=getattr(self, "server_id", None)).first()
            )
            if not db_row:
                db_row = User(
                    token=romm_id,
                    username=ru.get("username", "romm-user"),
                    email=ru.get("email", ""),
                    code="romm",  # placeholder – no invite code
                    password="romm",  # placeholder
                    server_id=getattr(self, "server_id", None),
                )
                db.session.add(db_row)
            else:
                db_row.username = ru.get("username", db_row.username)
                db_row.email = ru.get("email", db_row.email)
        db.session.commit()

        # 2) Remove local users that no longer exist upstream
        for local in (
            User.query.filter(User.server_id == getattr(self, "server_id", None)).all()
        ):
            if local.token not in remote_by_id:
                db.session.delete(local)
        db.session.commit()

        return (
            User.query.filter(User.server_id == getattr(self, "server_id", None)).all()
        )

    # ------------------------------------------------------------------
    # Un-implemented mutating operations
    # ------------------------------------------------------------------

    # Even though Wizarr currently doesn't expose UI to mutate RomM users, we
    # provide simple wrappers so future work (or API consumers) can call them.

    def create_user(self, username: str, password: str, email: str | None = None) -> str:
        """Create a RomM user and return the new ``user_id``.

        Only *username* and *password* are mandatory according to RomM docs.
        """
        payload: Dict[str, Any] = {
            "username": username,
            "password": password,
            "email": email,
            "role": "VIEWER",
        }

        # ------------------------------------------------------------------
        # Attempt 1 – query-string parameters (matches observed RomM behaviour)
        # ------------------------------------------------------------------
        try:
            r = self.post(f"{self.API_PREFIX}/users", params=payload)
        except requests.HTTPError as exc:
            r = exc.response  # type: ignore[assignment]

        # If the server expects JSON body instead, fall back once
        if r is not None and r.status_code == 422:
            try:
                logging.warning("ROMM create_user validation error (params): %s", r.json())
            except Exception:
                logging.warning("ROMM create_user validation 422 (params) with non-JSON body: %s", r.text)

            alt = payload.copy()
            alt["passwordConfirm"] = password  # older builds require this field

            try:
                r = self.post(f"{self.API_PREFIX}/users", json=alt)
            except requests.HTTPError as exc:
                r = exc.response  # type: ignore[assignment]

        data: Dict[str, Any] = {}
        try:
            if r is not None:
                data = r.json()
        except Exception:
            pass

        return data.get("id") or data.get("user", {}).get("id")  # type: ignore[return-value]

    def update_user(self, user_id: str, patch: Dict[str, Any]):
        """PATCH selected fields on a RomM user object."""
        return self.patch(f"{self.API_PREFIX}/users/{user_id}", json=patch).json()

    def delete_user(self, user_id: str):
        resp = self.delete(f"{self.API_PREFIX}/users/{user_id}")
        if resp.status_code not in (200, 204):
            resp.raise_for_status()

    def get_user(self, user_id: str) -> Dict[str, Any]:
        r = self.get(f"{self.API_PREFIX}/users/{user_id}")
        return r.json()

    # ------------------------------------------------------------------
    # Public sign-up via invites (same contract as other clients)
    # ------------------------------------------------------------------

    def _password_for_db(self, password: str) -> str:
        """Return value stored in local DB for the given raw password."""
        return password  # no hashing for now – keep consistent with other svc

    def now_playing(self) -> list[dict]:
        """Return a list of currently playing sessions from RomM.
        
        Note: RomM is a ROM/game collection management server that does not 
        provide session tracking or "now playing" functionality in its API.
        This method always returns an empty list.
        
        Returns:
            list: Always returns an empty list since RomM doesn't track active sessions.
        """
        # RomM API doesn't provide session/now-playing endpoints
        # It's focused on ROM collection management, not active gaming sessions
        logging.debug("ROMM: No session tracking available - RomM doesn't provide now-playing functionality")
        return []

    def statistics(self):
        """Return comprehensive RomM server statistics.
        
        Returns:
            dict: Server statistics including library counts, user activity, etc.
        """
        try:
            stats = {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {}
            }
            
            # Library statistics (platforms in RomM)
            try:
                platforms_response = self.get(f"{self.API_PREFIX}/platforms").json()
                library_stats = {}
                
                for platform in platforms_response:
                    platform_name = platform.get("name", platform.get("id", "unknown"))
                    
                    # Get ROM count for this platform
                    try:
                        roms_response = self.get(f"{self.API_PREFIX}/roms", params={
                            "platform_id": platform["id"],
                            "limit": 1,
                            "offset": 0
                        }).json()
                        
                        rom_count = roms_response.get("total", 0)
                        
                        # Group by console type/generation if possible
                        platform_type = "retro_gaming"  # RomM is all retro gaming
                        if platform_type not in library_stats:
                            library_stats[platform_type] = {
                                "count": 0,
                                "sections": []
                            }
                        
                        library_stats[platform_type]["count"] += rom_count
                        library_stats[platform_type]["sections"].append({
                            "name": platform_name,
                            "size": rom_count,
                            "id": platform["id"]
                        })
                    except Exception as e:
                        logging.warning(f"Failed to get ROM count for platform {platform_name}: {e}")
                        if "retro_gaming" not in library_stats:
                            library_stats["retro_gaming"] = {
                                "count": 0,
                                "sections": []
                            }
                        library_stats["retro_gaming"]["sections"].append({
                            "name": platform_name,
                            "size": 0,
                            "id": platform["id"]
                        })
                
                stats["library_stats"] = library_stats
            except Exception as e:
                logging.error(f"Failed to get RomM library stats: {e}")
                stats["library_stats"] = {}
            
            # User statistics
            try:
                users_response = self.get(f"{self.API_PREFIX}/users").json()
                total_users = len(users_response)
                
                # RomM doesn't have active sessions like media servers
                # It's a collection manager, not a streaming service
                stats["user_stats"] = {
                    "total_users": total_users,
                    "active_users": 0,  # No session concept in RomM
                    "active_sessions": 0
                }
            except Exception as e:
                logging.error(f"Failed to get RomM user stats: {e}")
                stats["user_stats"] = {
                    "total_users": 0,
                    "active_users": 0,
                    "active_sessions": 0
                }
            
            # Server statistics
            try:
                # RomM doesn't expose much server info via API
                # Get basic platform and ROM counts
                try:
                    platforms_response = self.get(f"{self.API_PREFIX}/platforms").json()
                    platform_count = len(platforms_response)
                except Exception:
                    platform_count = 0
                
                # Try to get total ROM count across all platforms
                try:
                    roms_response = self.get(f"{self.API_PREFIX}/roms", params={
                        "limit": 1,
                        "offset": 0
                    }).json()
                    total_roms = roms_response.get("total", 0)
                except Exception:
                    total_roms = 0
                
                stats["server_stats"] = {
                    "version": "Unknown",  # RomM doesn't expose version via API
                    "server_name": "RomM Server",
                    "total_platforms": platform_count,
                    "total_roms": total_roms,
                    "total_sessions": 0,  # Not applicable for RomM
                    "transcoding_sessions": 0  # Not applicable for RomM
                }
            except Exception as e:
                logging.error(f"Failed to get RomM server stats: {e}")
                stats["server_stats"] = {}
            
            # Content statistics
            try:
                content_stats = {
                    "recently_added": [],
                    "popular_platforms": [],
                    "largest_collections": []
                }
                
                # Get recently added ROMs
                try:
                    recent_roms = self.get(f"{self.API_PREFIX}/roms", params={
                        "limit": 5,
                        "offset": 0,
                        "order_by": "created_at",
                        "order_dir": "desc"
                    }).json()
                    
                    for rom in recent_roms.get("items", []):
                        content_stats["recently_added"].append({
                            "title": rom.get("name", "Unknown ROM"),
                            "type": "rom",
                            "added_at": rom.get("created_at"),
                            "platform": rom.get("platform_name", "Unknown Platform")
                        })
                except Exception as e:
                    logging.warning(f"Failed to get recently added ROMs: {e}")
                
                # Get platform stats for popular platforms
                try:
                    platforms_response = self.get(f"{self.API_PREFIX}/platforms").json()
                    platform_rom_counts = []
                    
                    for platform in platforms_response[:10]:  # Limit for performance
                        try:
                            roms_response = self.get(f"{self.API_PREFIX}/roms", params={
                                "platform_id": platform["id"],
                                "limit": 1
                            }).json()
                            rom_count = roms_response.get("total", 0)
                            platform_rom_counts.append({
                                "name": platform.get("name", platform["id"]),
                                "rom_count": rom_count,
                                "id": platform["id"]
                            })
                        except Exception:
                            platform_rom_counts.append({
                                "name": platform.get("name", platform["id"]),
                                "rom_count": 0,
                                "id": platform["id"]
                            })
                    
                    # Sort by ROM count and take top 5
                    platform_rom_counts.sort(key=lambda x: x["rom_count"], reverse=True)
                    content_stats["popular_platforms"] = platform_rom_counts[:5]
                    content_stats["largest_collections"] = platform_rom_counts[:5]
                    
                except Exception as e:
                    logging.warning(f"Failed to get platform statistics: {e}")
                
                stats["content_stats"] = content_stats
            except Exception as e:
                logging.error(f"Failed to get RomM content stats: {e}")
                stats["content_stats"] = {}
            
            return stats
            
        except Exception as e:
            logging.error(f"Failed to get RomM statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
                "error": str(e)
            }

    def join(
        self,
        *,
        username: str,
        password: str,
        confirm: str,
        email: str,
        code: str,
    ) -> tuple[bool, str]:
        """Handle public sign-up via invite for RomM servers."""

        if not EMAIL_RE.fullmatch(email):
            return False, "Invalid e-mail address."
        if not 8 <= len(password) <= 20:
            return False, "Password must be 8–20 characters."
        if password != confirm:
            return False, "Passwords do not match."

        ok, msg = is_invite_valid(code)
        if not ok:
            return False, msg

        existing = (
            User.query
            .filter(
                or_(User.username == username, User.email == email),
                User.server_id == getattr(self, "server_id", None),
            )
            .first()
        )
        if existing:
            return False, "User or e-mail already exists."

        try:
            # 1) create remotely – RomM returns the new user ID
            user_id = self.create_user(username, password, email=email)

            # 2) Determine which libraries (platforms) this invite grants
            inv = Invitation.query.filter_by(code=code).first()

            # Currently RomM doesn't expose per-platform permissions in API
            # (viewers can see everything).  We therefore don't attempt to
            # filter library access yet – we only need the DB linkage.

            expires = None
            if inv and inv.duration:
                days = int(inv.duration)
                expires = datetime.datetime.utcnow() + datetime.timedelta(days=days)

            new_user = User(
                username=username,
                email=email,
                token=user_id,
                code=code,
                expires=expires,
                server_id=inv.server.id if inv and inv.server else None,
            )
            db.session.add(new_user)
            db.session.commit()

            # mark invite used
            if inv:
                inv.used_by = new_user
                mark_server_used(inv, getattr(new_user, "server_id", None) or (inv.server.id if inv.server else None))

            notify("New User", f"User {username} has joined your server! 🎉", tags="tada")

            return True, ""

        except Exception:  # noqa: BLE001
            logging.error("ROMM join error", exc_info=True)
            db.session.rollback()
            return False, "An unexpected error occurred." 