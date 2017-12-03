# Manual instructions

These are the _basic_ steps to on-board a device in relayr's cloud.

## Retrieve token

Replace `user`, `password` and `organization` with your own.

````bash
TOKEN=$(curl --fail -v -d 'username=user&password=password&org=organization' 'https://login.relayr.io/oauth/token?client_id=api-client' 2>&1 | grep accessToken | jq --raw-output '.accessToken')
````

## Create device model

````bash
curl -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"name": "antonio-bonsai", "description": "Bonsai with sensors and self-watering system"}' -X POST "https://cloud.relayr.io/device-models/"
````

Response:

The `organization-id` was replaced, the `deviceModelID` is what you should use in the next step.

````bash
{
	"id": "deviceModelID",
	"orgId": "organization-id",
	"name": "antonio-bonsai",
	"description": "Bonsai with sensors and self-watering system",
	"updatedAt": "2017-12-03T20:10:50.357+0000",
	"createdAt": "2017-12-03T20:10:50.357+0000",
	"versionNumbers": []
}
````

## Create a device version

````bash
curl -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"measurements": [{"name": "temperature", "type": "number", "min": -100, "max": 100},{"name": "humidity", "type": "number", "min": 0, "max": 100},{"name": "pressure", "type": "number", "min": 600, "max": 1300},{"name": "soil_moist", "type": "number", "min": 0, "max": 2500}]}' -X POST "https://cloud.relayr.io/device-models/deviceModelID/versions"
````

Response:
````bash
{
	"versionNumber": 1,
	"modelId": "deviceModelID",
	"measurements": [{
		"name": "temperature",
		"type": "number",
		"min": -100,
		"max": 100
	}, {
		"name": "humidity",
		"type": "number",
		"min": 0,
		"max": 100
	}, {
		"name": "pressure",
		"type": "number",
		"min": 600,
		"max": 1300
	}, {
		"name": "soil_moist",
		"type": "number",
		"min": 0,
		"max": 2500
	}],
	"alerts": [],
	"commands": [],
	"createdAt": "2017-12-03T20:24:47.952+0000"
}
````

## Create a device

````bash
curl -XPOST -d '{"name": "Kodama", "modelId": "deviceModelID", "modelVersion": 1}' -H 'Content-Type: application/json' -v -H "Authorization: Bearer $TOKEN" https://cloud.relayr.io/devices/
````

Response:

The `deviceID` is retrieved and should be use to publish to the device.

````bash
Trying 52.58.184.223...
* TCP_NODELAY set
* Connected to cloud.relayr.io (52.58.184.223) port 443 (#0)
* TLS 1.2 connection using TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
* Server certificate: *.relayr.io
* Server certificate: SSL.com DV CA
* Server certificate: USERTrust RSA Certification Authority
> POST /devices/ HTTP/1.1
> Host: cloud.relayr.io
> User-Agent: curl/7.54.0
> Accept: */*
> Content-Type: application/json
> Authorization: Bearer XXXXXXXXXXXXXXXXXXXXXXXXX
> Content-Length: 88
> 
* upload completely sent off: 88 out of 88 bytes

< HTTP/1.1 201 Created
< Date: Sun, 03 Dec 2017 20:28:19 GMT
< Content-Type: application/json; charset=utf-8
< Content-Length: 260
< Connection: keep-alive
< Server: openresty
< Access-Control-Allow-Origin: *
< Access-Control-Allow-Methods: GET,HEAD,PUT,POST,DELETE
< 
* Connection #0 to host cloud.relayr.io left intact

{
	"id": "deviceID",
	"orgId": "organizationID",
	"name": "Kodama",
	"modelId": "deviceModelID",
	"modelVersion": 1,
	"updatedAt": "2017-12-03T20:28:18.789+0000",
	"createdAt": "2017-12-03T20:28:18.789+0000"
}
````