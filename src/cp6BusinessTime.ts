export const CP6_BUSINESS_TIME_ZONE = 'Asia/Jakarta'
export const CP6_BUSINESS_TIME_LABEL = 'WIB (Asia/Jakarta)'

const CP6_BUSINESS_UTC_OFFSET = '+07:00'
const localDateTimePattern = /^(\d{4})-(\d{2})-(\d{2})T([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$/

function daysInMonth(year: number, month: number) {
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)
  return [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1] ?? 0
}

/**
 * Converts an operator-entered wall-clock time using the ERP business timezone,
 * never the browser/device timezone. Asia/Jakarta is UTC+07:00 without DST.
 */
export function cp6WibPhysicalTimeToIso(value: string) {
  const match = localDateTimePattern.exec(value.trim())
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > daysInMonth(year, month)) return null
  const seconds = match[6] ?? '00'
  const instant = new Date(`${match[1]}-${match[2]}-${match[3]}T${match[4]}:${match[5]}:${seconds}${CP6_BUSINESS_UTC_OFFSET}`)
  return Number.isNaN(instant.getTime()) ? null : instant.toISOString()
}

export function formatCp6WibDateTime(value: string) {
  const instant = new Date(value)
  if (Number.isNaN(instant.getTime())) return 'Waktu tidak valid'
  return `${instant.toLocaleString('id-ID', {
    timeZone: CP6_BUSINESS_TIME_ZONE,
    dateStyle: 'medium',
    timeStyle: 'short',
    hour12: false,
  })} WIB`
}
