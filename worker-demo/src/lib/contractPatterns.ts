// Text formats shared by ERP response readers. Each reader still validates its own ranges, dates and document links.
export const lowercaseUuidText = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
export const uuidText = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
export const versionedUuidText = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
export const isoDayText = /^\d{4}-\d{2}-\d{2}$/
export const lowercaseHex32 = /^[0-9a-f]{32}$/
export const lowercaseHex64 = /^[0-9a-f]{64}$/
export const positive19Digits = /^[1-9][0-9]{0,18}$/
export const unsigned19Digits = /^(0|[1-9][0-9]{0,18})$/
export const timestampWithZone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/
