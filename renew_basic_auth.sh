#!/bin/bash

varLookup(){
    name=$1
    basicAuthFile=$(grep -r get${name^} $SOURCE |grep public |grep amazon | grep final | awk -F ':' '{ print $1}')
    varName=$(grep get${name^} $basicAuthFile -A 4 | tail -1 | awk '{print $3}' | rev | cut -c 2- | rev)
    value=$(grep -E "put-object.*$varName" $basicAuthFile -B 4 | grep const | awk -F '"' '{ print $2}')
    echo $value
}

LATEST=$(curl -s --location -I "https://d.apkpure.net/b/APK/com.crunchyroll.crunchyroid?version=latest" | grep Content-Disposition | awk -F '"' '{ print $2}' | awk -F '_' '{ print $2}')
CURRENT=$(ls -v "./decompiled_crunchyroll/" | tail -n1)
echo "Last version available=$LATEST"
echo "Current version=$CURRENT"
if [ "$CURRENT" != "$LATEST" ]; then
    cd "./apk/"
    wget --content-disposition https://d.apkpure.net/b/APK/com.crunchyroll.crunchyroid?version=latest
    cd ..
    VERSION=$LATEST
    apktool d ./apk/Crunchyroll_${VERSION}_Apkpure.apk -o "./decompiled_crunchyroll/$VERSION"
    SOURCE="./decompiled_crunchyroll/$VERSION"
    clientId=$(varLookup "clientId")
    clientSecret=$(varLookup "clientSecret")
    appVersion=$VERSION
    androidVersion=$(grep -r "android:compileSdkVersionCodename" "$SOURCE" | awk -F "android:compileSdkVersionCodename" '{ print $2}' | awk -F '"' '{ print $2}')
    okhttpVersion=$(grep -r "VERSION" "$SOURCE" |grep String | grep okhttp | grep '=' | awk -F '"' '{print $2}')

    echo "clientId=$clientId"
    echo "clientSecret=$clientSecret"
    echo "appVersion=$appVersion"
    echo "androidVersion=$androidVersion"
    echo "okhttpVersion=$okhttpVersion"

    basicAuth=$(echo -n "$clientId:$clientSecret" | base64)
    userAgent="\"Crunchyroll/$appVersion Android/$androidVersion okhttp/$okhttpVersion\""

    sed -i "s|^CRUNCHYROLL_UA.*\$|CRUNCHYROLL_UA = $userAgent|" plugin.video.crunchyroll/resources/lib/utils.py
    sed -i "s|^\(\\s*\)\"Authorization\".*|\\1\"Authorization\": \"Basic $basicAuth\"|" plugin.video.crunchyroll/resources/lib/auth.py
else
    echo "Nothing to do, we are up to date"
fi

