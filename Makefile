
install: clean
	cp -r src "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

clean:
	rm -rf "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

test:
	pylint $$(find -name *.py -not -path "./.venv/*")
	flake8
	.venv/bin/nosetests -v

.PHONY: clean
