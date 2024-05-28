SHELL=/usr/bin/bash
SOURCE_FOLDER="plugin.video.crunchyreroll"
CRUNCHYROLL_VERSION := $(shell xq -r '.addon."@version"' plugin.video.crunchyreroll/addon.xml)
REPO="https://api.github.com/repos/xtero/CrunchyREroll/releases"
ARCHIVE="archive/plugin.video.crunchyreroll-${CRUNCHYROLL_VERSION}.zip"

install: clean
	cp -r ${SOURCE_FOLDER} "${KODI_INSTALL}/addons/plugin.video.crunchyreroll"

clean:
	rm -rf "${KODI_INSTALL}/addons/plugin.video.crunchyreroll"

test: lint
	.venv/bin/pytest tests

cleanup:
	FOLDERS=$$(find . -name __pycache__ -not -path "./.venv/*") &&\
	for folder in $${FOLDERS[@]}; do rm -r $$folder; done

lint: cleanup
	.venv/bin/pylint $$(find -name *.py -not -path "./.venv/*")
	.venv/bin/flake8
#	.venv/bin/kodi-addon-checker --branch  nexus ${SOURCE_FOLDER}

clean-release:
	rm -rf release

$(ARCHIVE):
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
	cd release; zip -r ../archive/plugin.video.crunchyreroll-${CRUNCHYROLL_VERSION}.zip *

release-upload:
	curl -X POST -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28"  -H "Authorization: Bearer $${CRUNCHYROLL_GITHUB_TOKEN}" ${REPO} \
	-d '{"tag_name":"v${CRUNCHYROLL_VERSION}","target_commitish":"main","name":"v${CRUNCHYROLL_VERSION}","body":"New Crunchyroll Release v${CRUNCHYROLL_VERSION}","draft":false,"prerelease":false,"generate_release_notes":false}' -o release_${CRUNCHYROLL_VERSION}.json
	curl -v -X POST -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28"  -H "Authorization: Bearer $${CRUNCHYROLL_GITHUB_TOKEN}" \
	"$$(jq -r .upload_url release_${CRUNCHYROLL_VERSION}.json | awk -F '{' '{ print $$1}')?name=plugin.video.crunchyreroll-${CRUNCHYROLL_VERSION}.zip" \
	-H "Content-Type: application/zip" --data-binary @archive/plugin.video.crunchyreroll-${CRUNCHYROLL_VERSION}.zip
	rm release_${CRUNCHYROLL_VERSION}.json

release: clean-release test $(ARCHIVE) release-upload

.PHONY: clean clean-release test lint install
