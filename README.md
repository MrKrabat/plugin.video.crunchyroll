# Crunchyroll plugin for Kodi

Crunchyroll is a KODI (XBMC) plugin for Crunchyroll.com.

**WARNING: You MUST be a PREMIUM member to use this plugin!**
**This plugin does not intend to let you do illegal stuff**
***

**Before playing videos, don't forget to install Widevine CDM**
**InputStream Helper will do the job for you. Go in your Addon->My Addon->Addon Script->InpustStream Helper**

_This page and addon are not affiliated with Crunchyroll._

_Kodi® (formerly known as XBMC™) is a registered trademark of the XBMC Foundation.
This page and addon are not affiliated with Kodi, Team Kodi, or the XBMC Foundation._


# Contributors

Original creator: MrKrabat  
Maintainer: Xtero
Contributors:
- Smirgo
- TheFantasticLoki
- robofunk
- APachecoDiSanti
- jasonfrancis
- vlfr1997
- Nux007

Git repo: https://github.com/xtero/plugin.video.crunchyroll

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
- [ ] Add or remove anime from your queue/playlist
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

