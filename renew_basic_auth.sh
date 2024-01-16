#!/bin/bash

VERSION="3.47.0"
SOURCE="./decompiled_crunchyroll/$VERSION"

varLookup(){
    name=$1
    basicAuthFile=$(grep -r get${name^} $SOURCE |grep public |grep amazon | awk -F ':' '{ print $1}')
    varName=$(grep get${name^} $basicAuthFile -A 1 | tail -1 | awk '{print $2}' | cut -c -1)
    value=$(grep "String $varName" $basicAuthFile | awk -F " = " '{ print $2}' | cut -c 2- | rev | cut -c 3- | rev)
    echo $value
}

clientId=$(varLookup "clientId")
clientSecret=$(varLookup "clientSecret")
appVersion=$(grep -r "android:versionName" "$SOURCE" | awk -F "android:versionName" '{ print $2}' | awk -F '"' '{ print $2}')
androidVersion=$(grep -r "android:compileSdkVersionCodename" "$SOURCE" | awk -F "android:compileSdkVersionCodename" '{ print $2}' | awk -F '"' '{ print $2}')
okhttpVersion=$(grep -r "String VERSION =" "$SOURCE" | grep okhttp | awk -F '"' '{print $2}')

echo "clientId=$clientId"
echo "clientSecret=$clientSecret"
echo "appVersion=$appVersion"
echo "androidVersion=$androidVersion"
echo "okhttpVersion=$okhttpVersion"

basicAuth=$(echo -n "$clientId:$clientSecret" | base64)
userAgent="\"Crunchyroll/$appVersion Android/$androidVersion okhttp/$okhttpVersion\""

sed -i "s|^CRUNCHYROLL_UA.*\$|CRUNCHYROLL_UA = $userAgent|" src/resources/lib/utils.py
sed -i "s|^\(\\s*\)\"Authorization\".*|\\1\"Authorization\": \"Basic $basicAuth\"|" src/resources/lib/auth.py
