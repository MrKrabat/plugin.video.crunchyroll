SHELL=/usr/bin/bash
SOURCE_FOLDER="plugin.video.crunchyroll"
CRUNCHYROLL_VERSION := $(shell xq -r '.addon."@version"' plugin.video.crunchyroll/addon.xml)

install: clean
	cp -r ${SOURCE_FOLDER} "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

clean:
	rm -rf "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

test: lint
	.venv/bin/pytest

lint:
	.venv/bin/pylint $$(find -name *.py -not -path "./.venv/*")
	.venv/bin/flake8

clean-release:
	rm -rf release

release: clean-release test
	mkdir -p release/resources/lib/
	cp ${SOURCE_FOLDER}/resources/lib/*.py release/resources/lib/
	cp ${SOURCE_FOLDER}/resources/*.py release/resources/
	cp ${SOURCE_FOLDER}/*.py release/
	mkdir -p release/resources/language
	cp -r ${SOURCE_FOLDER}/resources/language release/resources/
	mkdir -p release/resources/media
	cp ${SOURCE_FOLDER}/resources/media/* release/resources/media
	cp ${SOURCE_FOLDER}/resources/settings.xml release/resources/settings.xml
	cp ${SOURCE_FOLDER}/{addon.xml,changelog.txt,fanart.jpg,icon.png} release/
	mkdir -p archive
	cd release; zip -r ../archive/plugin.video.crunchyroll-${CRUNCHYROLL_VERSION}.zip *

.PHONY: clean clean-release
