
install: clean
	mkdir "${KODI_INSTALL}/addons/plugin.video.crunchyroll"
	cp -r resources "${KODI_INSTALL}/addons/plugin.video.crunchyroll"
	cp addon.xml default.py fanart.jpg icon.png "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

clean:
	rm -rf "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

.PHONY: clean
