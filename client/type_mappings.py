# These types must fit with the kafka topic postfixes in config.json of the client.
# from http://www.opengis.net/def/observationType/OGC-OM/2.0
type_mappings = dict({
  "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_TruthObservation": bool,
  "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_CountObservation": int,
  "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement": float,
  "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_CategoryObservation": str,
  "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Observation": dict,
  "logging": str
})
