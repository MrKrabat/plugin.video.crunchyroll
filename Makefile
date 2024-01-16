SHELL=/usr/bin/bash
CRUNCHYROLL_VERSION := $(shell xq -r '.addon."@version"' src/addon.xml)

install: clean
	cp -r src "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

clean:
	rm -rf "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

test: lint
	.venv/bin/pytest

lint:
	.venv/bin/pylint $$(find -name *.py -not -path "./.venv/*")
	.venv/bin/flake8

clean-release:
	rm -rf release

release: clean-release
	mkdir -p release/resources/lib/
	cp src/resources/lib/*.py release/resources/lib/
	cp src/resources/*.py release/resources/
	cp src/*.py release/
	mkdir -p release/resources/language
	cp -r src/resources/language release/resources/language
	mkdir -p release/resources/media
	cp src/resources/media/* release/resources/media
	cp src/resources/settings.xml release/resources/settings.xml
	cp src/{addon.xml,changelog.txt,fanart.jpg,icon.png} release/
	mkdir -p archive
	cd release; zip -r ../archive/plugin.video.crunchryoll-${CRUNCHYROLL_VERSION}.zip *

.PHONY: clean clean-release
