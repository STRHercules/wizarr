from .admin.routes import admin_bp
from .auth.routes  import auth_bp
from .settings.routes import settings_bp
from .setup.routes    import setup_bp
from .public.routes  import public_bp
from .wizard.routes  import wizard_bp
from .plex.routes import plex_bp
from .notifications.routes import notify_bp
from .jellyfin.routes import jellyfin_bp
from .api.status import status_bp
from .emby.routes import emby_bp
from .media_servers.routes import media_servers_bp
from .audiobookshelf.routes import abs_bp
from .wizard_admin.routes import wizard_admin_bp
from .admin_accounts.routes import admin_accounts_bp

all_blueprints = (public_bp, wizard_bp, admin_bp, auth_bp,
                  settings_bp, setup_bp, plex_bp, notify_bp, jellyfin_bp, emby_bp, abs_bp, status_bp,
                  media_servers_bp, wizard_admin_bp, admin_accounts_bp)
