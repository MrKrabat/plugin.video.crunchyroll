# Crunchyroll plugin for Kodi

CrunchyREroll is a KODI (XBMC) plugin for Crunchyroll.com.

**WARNING: You MUST be a PREMIUM member to use this plugin!**
**This plugin does not intend to let you do illegal stuff**
***

**This plugin support DRM streams**
**Even if you didn't installed Widevice CDM, the plugin will propose you to install it before playing an episode**

***
_This page and addon are not affiliated with Crunchyroll._

_Kodi® (formerly known as XBMC™) is a registered trademark of the XBMC Foundation.
This page and addon are not affiliated with Kodi, Team Kodi, or the XBMC Foundation._
***

# Installation and update
A repository have been created to help you install the plugin and keep it up to date.  
To install the repo, please download the file https://github.com/xtero/crunchyreroll-repo/raw/main/repository.crunchyreroll-1.0.0.zip  
On Kodi, use the feature "Install from zip" to install the repo.  
Once it's done, you can update your plugin from the repo.   

# Contributors

Maintainer: Xtero  

Contributors:
- Smirgo

Git repo: https://github.com/xtero/CrunchyREroll

# Features

What this plugin currently can do:
- [x] Supports all Crunchyroll regions
- [x] Login with your account
- [x] Search for animes
- [x] Browse all popular anime
- [x] Browse all simulcasts
- [x] Browse all new anime
- [x] Browse all anime alphabetically
- [x] Browse all genres
- [x] Browse all seasons
- [x] Browse Crunchylists
- [x] View history
- [x] View all seasons/arcs of an anime
- [x] View all episodes of an season/arc
- [x] Display various informations
- [x] Watch videos with premium subscription
- [x] Synchronizes playback stats with Crunchyroll
***

# How to run tests
If you are using a Linux distro, you probably can run the bootstrap.sh script.  
It will ensure that you have all required dependencies in the freshly created Python VirtualEnv.  
This virtualenv is stored in the folder .venv.

Before running tests, you need to defined enviroment variable CRUNCHYROLL_EMAIL and CRUNCHYROLL_PASSWORD.
On my side, I used to do it through my .bash_aliases. But you can do it the way you like it :)  

If you don't like Makefile, you can just run pytest.
Otherwise, you can use `make test` that will also run pylint and flake8 on the code to ensure a minimal quality level.

