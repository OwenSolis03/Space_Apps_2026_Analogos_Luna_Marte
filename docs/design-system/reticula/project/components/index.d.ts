import * as React from "react";

export type GlyphName =
  | "plus" | "close" | "tick-left" | "tick-right" | "bracket" | "corner"
  | "slash" | "slash-pair" | "chevron-down" | "chevron-right" | "dots" | "dot";

export interface PanelProps {
  /** Color del mosaico. "raised" es el blanco; por defecto "raised". */
  tone?: "raised" | "signal" | "tint" | "graphite" | "sunken" | "outline";
  /** Corte de 45° arriba a la derecha. Por defecto true. */
  chamfer?: boolean;
  /** Etiqueta superior en mini mono. */
  label?: string;
  /** Segunda línea bajo la etiqueta. */
  note?: string;
  /** Código grande abajo a la izquierda (A0., 2.C). */
  code?: string;
  /** Muestra el grupo de cuatro puntos abajo a la derecha. */
  marks?: boolean;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export interface TagProps {
  tone?: "graphite" | "signal" | "outline";
  /** Envuelve el texto en [ corchetes ]. */
  bracket?: boolean;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export interface ButtonProps {
  variant?: "primary" | "secondary";
  /** Añade el chevron de avance a la derecha. */
  arrow?: boolean;
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export interface IconButtonProps {
  /** Nombre accesible obligatorio: el botón no lleva texto. */
  label: string;
  glyph?: GlyphName;
  /** Estado activo: anillo en `ink` y marca naranja a la izquierda. */
  pressed?: boolean;
  disabled?: boolean;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  className?: string;
  style?: React.CSSProperties;
}

export interface ProgressProps {
  /** Texto de la lectura, p. ej. "CARGA". */
  label: string;
  /** Valor entre 0 y 1. */
  value: number;
  /** Cola de rayas de peligro. Por defecto true. */
  hazard?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export interface ReadoutItem {
  label: string;
  value: string;
  /** Muestra el valor como Tag (estado) en lugar de texto. */
  status?: boolean;
  tone?: "graphite" | "signal" | "outline";
}
export interface ReadoutProps {
  title?: string;
  items: ReadoutItem[];
  className?: string;
  style?: React.CSSProperties;
}

export interface HeadlineProps {
  title: string;
  kicker?: string;
  subtitle?: string;
  by?: string;
  /** lg = display-a, md = display-c, sm = headline. Por defecto md. */
  size?: "lg" | "md" | "sm";
  /** Color de la regla superior. Por defecto "signal". */
  rule?: "signal" | "graphite";
  /** Elemento HTML del título. Por defecto h2. */
  as?: "h1" | "h2" | "h3" | "h4";
  className?: string;
  style?: React.CSSProperties;
}

export interface FrameProps {
  /** Proporción CSS, p. ej. "16 / 9". */
  ratio?: string;
  caption?: string;
  /** Descripción accesible de la imagen que irá aquí. */
  label?: string;
  className?: string;
  style?: React.CSSProperties;
}

export interface HazardProps {
  tone?: "graphite" | "signal";
  height?: number | string;
  width?: number | string;
  className?: string;
  style?: React.CSSProperties;
}

export interface DotGridProps {
  cols?: number;
  rows?: number;
  tone?: "graphite" | "faint" | "signal";
  /** Barra naranja guía a la izquierda. */
  lead?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export interface BarcodeProps {
  /** Anchos relativos; los pares se rellenan y los impares quedan vacíos. */
  segments?: number[];
  tone?: "signal" | "ink" | "graphite";
  className?: string;
  style?: React.CSSProperties;
}

export interface GlyphProps {
  name: GlyphName;
  size?: number;
  tone?: "ink" | "muted" | "graphite" | "signal";
  /** Si se da, el glifo es una imagen con nombre; si no, es decorativo. */
  label?: string;
  className?: string;
  style?: React.CSSProperties;
}

export const Panel: React.FC<PanelProps>;
export const Tag: React.FC<TagProps>;
export const Button: React.FC<ButtonProps>;
export const IconButton: React.FC<IconButtonProps>;
export const Progress: React.FC<ProgressProps>;
export const Readout: React.FC<ReadoutProps>;
export const Headline: React.FC<HeadlineProps>;
export const Frame: React.FC<FrameProps>;
export const Hazard: React.FC<HazardProps>;
export const DotGrid: React.FC<DotGridProps>;
export const Barcode: React.FC<BarcodeProps>;
export const Glyph: React.FC<GlyphProps>;
