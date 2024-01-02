
install: clean
	cp -r src "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

clean:
	rm -rf "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

test:
	.venv/bin/nosetests -v

.PHONY: clean
