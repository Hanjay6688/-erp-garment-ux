// Real SHA-256 provider for isolated jsdom tests, never part of browser code.
import {createHash,webcrypto} from 'node:crypto'
export const reportCrypto=webcrypto
export const reportBodyDigest=value=>createHash('sha256').update(value,'utf8').digest('hex')
