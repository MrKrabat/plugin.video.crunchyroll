SHELL=/usr/bin/bash
SOURCE_FOLDER="plugin.video.crunchyroll"
CRUNCHYROLL_VERSION := $(shell xq -r '.addon."@version"' plugin.video.crunchyroll/addon.xml)

install: clean
	cp -r ${SOURCE_FOLDER} "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

clean:
	rm -rf "${KODI_INSTALL}/addons/plugin.video.crunchyroll"

test: lint
	.venv/bin/pytest

cleanup:
	FOLDERS=$$(find . -name __pycache__ -not -path "./.venv/*") &&\
	for folder in $${FOLDERS[@]}; do rm -r $$folder; done

lint: cleanup
	.venv/bin/pylint $$(find -name *.py -not -path "./.venv/*")
	.venv/bin/flake8
	.venv/bin/kodi-addon-checker --branch  nexus ${SOURCE_FOLDER}

clean-release:
	rm -rf release

release: clean-release test
	mkdir -p release/${SOURCE_FOLDER}/resources/lib/
	cp ${SOURCE_FOLDER}/resources/lib/*.py release/${SOURCE_FOLDER}/resources/lib/
	cp ${SOURCE_FOLDER}/resources/*.py release/${SOURCE_FOLDER}/resources/
	cp ${SOURCE_FOLDER}/*.py release/${SOURCE_FOLDER}/
	mkdir -p release/${SOURCE_FOLDER}/resources/language
	cp -r ${SOURCE_FOLDER}/resources/language release/${SOURCE_FOLDER}/resources/
	mkdir -p release/${SOURCE_FOLDER}/resources/media
	cp ${SOURCE_FOLDER}/resources/media/* release/${SOURCE_FOLDER}/resources/media
	cp ${SOURCE_FOLDER}/resources/settings.xml release/${SOURCE_FOLDER}/resources/settings.xml
	cp ${SOURCE_FOLDER}/{addon.xml,changelog.txt,fanart.jpg,icon.png} release/${SOURCE_FOLDER}/
	mkdir -p archive
	cd release; zip -r ../archive/plugin.video.crunchyroll-${CRUNCHYROLL_VERSION}.zip *

.PHONY: clean clean-release
