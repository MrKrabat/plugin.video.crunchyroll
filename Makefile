
install: clean
	cp -r src "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

clean:
	rm -rf "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

test: lint
	.venv/bin/pytest

lint:
	pylint $$(find -name *.py -not -path "./.venv/*")
	flake8

.PHONY: clean
