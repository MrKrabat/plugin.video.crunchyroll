SHELL=/usr/bin/bash
REPO="https://api.github.com/repos/xtero/CrunchyREroll/releases"
ARCHIVE="archive/plugin.video.crunchyreroll-${VERSION}.zip"
AUTHOR="Xtero"
PLUGIN_NAME="plugin.video.crunchyreroll"
SOURCE_FOLDER="plugin.video.crunchyreroll"

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

changelog:
	export LAST_TAG=$$(git describe --tags --abbrev=0) &&\
	export CHANGELOG=$$(git log "v1.0.4"..HEAD --pretty=format:"- %s") &&\
	export DATE=$$(date +%Y-%m-%d) &&\
	echo -e "v${VERSION}($${DATE})\n$${CHANGELOG}\n" > changelog
	cat changelog plugin.video.crunchyreroll/changelog.txt > tmp && mv tmp plugin.video.crunchyreroll/changelog.txt
	mkdir -p release/${SOURCE_FOLDER}
	export AUTHOR=${AUTHOR} &&\
	export CHANGELOG=$$(sed -e 's/^/            /' changelog) &&\
	export VERSION=${VERSION} &&\
	envsubst < ${SOURCE_FOLDER}/addon.xml > release/${SOURCE_FOLDER}/addon.xml

copy: clean-release
	mkdir -p release/${SOURCE_FOLDER}/resources/lib/
	cp ${SOURCE_FOLDER}/resources/lib/*.py release/${SOURCE_FOLDER}/resources/lib/
	cp ${SOURCE_FOLDER}/resources/*.py release/${SOURCE_FOLDER}/resources/
	cp ${SOURCE_FOLDER}/*.py release/${SOURCE_FOLDER}/
	mkdir -p release/${SOURCE_FOLDER}/resources/language
	cp -r ${SOURCE_FOLDER}/resources/language release/${SOURCE_FOLDER}/resources/
	mkdir -p release/${SOURCE_FOLDER}/resources/media
	cp ${SOURCE_FOLDER}/resources/media/* release/${SOURCE_FOLDER}/resources/media
	cp ${SOURCE_FOLDER}/resources/settings.xml release/${SOURCE_FOLDER}/resources/settings.xml
	cp ${SOURCE_FOLDER}/{changelog.txt,fanart.jpg,icon.png} release/${SOURCE_FOLDER}/

license:
	FILES=$$(find -name *.py -path "./release/*") &&\
	export AUTHOR=${AUTHOR} &&\
	export YEAR=$$(date +%Y) &&\
	export PLUGIN_NAME=${PLUGIN_NAME} &&\
	export LICENSE_HEADER=$$(envsubst < license_header) &&\
	for file in $${FILES[@]}; do cat $$file | envsubst > tmp; mv tmp $$file; done

$(ARCHIVE): changelog copy license
	mkdir -p archive
	cd release; zip -r ../archive/plugin.video.crunchyreroll-${VERSION}.zip *

release-upload:
	curl -X POST -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28"  -H "Authorization: Bearer $${CRUNCHYROLL_GITHUB_TOKEN}" ${REPO} \
	-d '{"tag_name":"v${VERSION}","target_commitish":"main","name":"v${VERSION}","body":"New Crunchyroll Release v${VERSION}","draft":false,"prerelease":false,"generate_release_notes":false}' -o release_${VERSION}.json
	curl -v -X POST -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28"  -H "Authorization: Bearer $${CRUNCHYROLL_GITHUB_TOKEN}" \
	"$$(jq -r .upload_url release_${VERSION}.json | awk -F '{' '{ print $$1}')?name=plugin.video.crunchyreroll-${VERSION}.zip" \
	-H "Content-Type: application/zip" --data-binary @archive/plugin.video.crunchyreroll-${VERSION}.zip
	rm release_${VERSION}.json

check:
	if [ -z "${VERSION}" ]; then exit 1; fi
	if [ "$$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then exit 1; fi
	if [ ! -z "$$(git rev-list @{u}..HEAD)" ]; then exit 1; fi

release: check test $(ARCHIVE) release-upload

.PHONY: clean clean-release test lint install changelog
