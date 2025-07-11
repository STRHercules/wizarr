# Wizarr (Windows Bare‑Metal Edition)

> 🚀 **Development Relaunched:** This is a **community‑driven fork** of the original [Wizarr](https://github.com/wizarrrr/wizarr) that runs **natively as a Windows service—no Docker required.**

<p align="center"><img src="./app/static/wizarr-logo.png" height="200"></p>

---

Wizarr is an automatic user‑invitation system for Plex, Jellyfin, Emby, and AudiobookShelf.  
With this fork you can install **directly on bare‑metal Windows** (10/11 or Server 2019+) and have it run quietly in the background as a Windows Service—perfect for home‑labbers who prefer to skip container overhead.

## ❓ Why a Windows‑Service Fork?

| Pain Point | How this Fork Helps |
|------------|---------------------|
| **Docker required** on the original project | No container runtime needed—just run the bundled installer or PowerShell script. |
| Extra complexity for newcomers | Familiar Windows Service Manager controls start‑up, automatic restarts, and log routing. |
| Limited visibility into the host FS | Full access to local paths for media, config, & logs without volume mapping. |
| Running Docker on Windows Home | Completely unnecessary—this fork works on all modern Windows SKUs. |

---

## ✨ Major Features

- Automatic invitations for Plex, Jellyfin, Emby & AudiobookShelf
- Secure, user‑friendly invitation flow
- Plug‑and‑play SSO support*
- Multi‑tiered invitation access
- Time‑limited membership options
- Setup guide for media apps (e.g., Plex)
- Request‑system integration (Overseerr, Ombi, etc.)
- Discord invite support
- Fully customisable via your own HTML snippets

> \*SSO tested with Authentik & Keycloak on local network deployments.

---

## 🏃‍♂️ Getting Started (Windows Bare‑Metal)

1. **Download the latest release** from the [Releases page](https://github.com/YOUR‑FORK/wizarr‑windows/releases).  
   Choose the `Wizarr‑Setup-x64.msi` if you want a classic installer, or grab the ZIP if you prefer manual placement.
2. **Run the installer**.  
   - Registers the Wizarr Windows Service under `LocalSystem` (customisable).  
   - Opens a browser to `http://localhost:5690` on first start.
3. **Follow the onboarding wizard** to link Plex/Jellyfin/Emby & set up your first invite.
4. **[Optional] Update / Uninstall** through *Apps → Installed Apps* or via `sc delete Wizarr` for manual ZIP installs.

### Upgrading

Simply run the new MSI over the old install or replace the extracted files. The service will restart automatically.

---

## 🛠️ Advanced / Manual Installation

Prefer PowerShell? Run:

```powershell
irm https://raw.githubusercontent.com/YOUR-FORK/wizarr-windows/main/install.ps1 | iex
```

This script:

1. Downloads the latest portable build to `C:\Program Files\Wizarr`  
2. Creates & starts a service named **`Wizarr`**
3. Adds firewall rules for the default port (5690)

---

## 🤝 Fork & Credits

This project is a **soft fork** of the fantastic original work by the [Wizarr team](https://github.com/wizarrrr/wizarr).  
All upstream features & fixes are periodically merged—see `CHANGELOG.md` for details.

> Original licence: GPL‑3.0.  
> This fork inherits the same licence; contributions are welcome!

---

## 🌍 Translations

We use Weblate to make Wizarr accessible in many languages.  
Want to help translate? Click below!

<a href="https://hosted.weblate.org/engage/wizarr/"><img src="https://hosted.weblate.org/widget/wizarr/wizarr-universal/287x66-grey.png" alt="Translation status" /></a>

---

## 📸 Screenshots

![Accept Invite](./screenshots/accept_invite.jpeg)
![Home](./screenshots/home.jpeg)
![Invitations](./screenshots/invitations.jpeg)
![Settings](./screenshots/settings.jpeg)
![Users](./screenshots/users.jpeg)
![Wizarr](./screenshots/wizard.jpeg)

---

## ❤️ Thank You

A huge shout‑out to everyone who has contributed patches, bug reports, and translations—your help is what keeps this project alive!

<p align="center">
  <a href="https://github.com/YOUR-FORK/wizarr-windows/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=YOUR-FORK/wizarr-windows" />
  </a>
</p>
