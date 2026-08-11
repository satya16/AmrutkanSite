const DEV_DIGITS = ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९']

export function toDevanagari(n: number | string): string {
  return String(n)
    .split('')
    .map((c) => (c >= '0' && c <= '9' ? DEV_DIGITS[+c] : c))
    .join('')
}
