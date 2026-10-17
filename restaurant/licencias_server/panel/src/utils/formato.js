/** Formatea fechas, dinero y estados para mostrar en la interfaz. */
import { addDays, format, parseISO } from 'date-fns'
import { es } from 'date-fns/locale'

/** Símbolo de la moneda con la que se cobran las licencias. Cámbialo aquí. */
export const SIMBOLO_MONEDA = 'RD$'

const fmtMoneda = (() => {
  try {
    return new Intl.NumberFormat('es-DO', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  } catch {
    // Navegador sin el locale es-DO: separador de miles genérico.
    return new Intl.NumberFormat('es', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  }
})()

/**
 * Formatea un precio. Acepta el string que devuelve la API ("1500.00") o un
 * número; si no es válido muestra 0.00 en vez de "NaN".
 */
export function dinero(valor) {
  const n = Number(valor)
  return `${SIMBOLO_MONEDA}${fmtMoneda.format(Number.isFinite(n) ? n : 0)}`
}

export function fecha(iso) {
  if (!iso) return '—'
  try {
    return format(parseISO(iso), "d 'de' MMMM 'de' yyyy", { locale: es })
  } catch {
    return iso
  }
}

export function fechaCorta(iso) {
  if (!iso) return '—'
  try {
    return format(parseISO(iso), 'dd/MM/yyyy')
  } catch {
    return iso
  }
}

/** Estado visual de una licencia según días restantes y si está activa. */
export function estadoLicencia(licencia) {
  if (!licencia.activa) {
    return { etiqueta: 'Pausada', clase: 'neutro' }
  }
  const dias = licencia.dias_restantes
  if (dias === null || dias === undefined) {
    return { etiqueta: 'Sin vencimiento', clase: 'neutro' }
  }
  if (dias < 0) {
    return { etiqueta: `Vencida (${Math.abs(dias)}d)`, clase: 'peligro' }
  }
  if (dias <= 30) {
    return { etiqueta: `Vence en ${dias}d`, clase: 'alerta' }
  }
  return { etiqueta: `Activa (${dias}d)`, clase: 'exito' }
}

export function limiteTexto(valor) {
  return !valor ? 'Sin límite' : valor
}

/**
 * ¿Esta licencia ya toca cobrar el mes?
 *
 * Vence dentro de 30 días, está pausada o ya venció. Con la venta mensual son
 * las que hay que pasar por caja antes de que el POS pierda la licencia.
 */
export function tocaCobrar(licencia) {
  if (!licencia.activa) return true
  const dias = licencia.dias_restantes
  if (dias === null || dias === undefined) return true
  return dias <= DIAS_MENSUALIDAD
}

/** Fecha a la que quedaría la licencia tras `dias` más, sin tocar la BD. */
export function trasDias(iso, dias) {
  try {
    return format(addDays(parseISO(iso), dias), 'yyyy-MM-dd')
  } catch {
    return null
  }
}

/**
 * Vigencia por defecto de una licencia nueva.
 *
 * La venta es mensual, así que 30 días. Para una venta anual pasa `365`
 * explícitamente en lugar de cambiar este valor.
 */
export function vencimientoPorDefecto(dias = 30) {
  const f = new Date()
  f.setDate(f.getDate() + dias)
  return format(f, 'yyyy-MM-dd')
}

/** Días que suma "Actualizar mensualidad". Debe coincidir con el backend. */
export const DIAS_MENSUALIDAD = 30