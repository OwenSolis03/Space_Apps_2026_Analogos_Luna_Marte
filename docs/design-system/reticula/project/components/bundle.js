/* @ds-bundle: {"format":4,"namespace":"Reticula","components":[{"name":"Panel"},{"name":"Tag"},{"name":"Button"},{"name":"IconButton"},{"name":"Progress"},{"name":"Readout"},{"name":"Headline"},{"name":"Frame"},{"name":"Hazard"},{"name":"DotGrid"},{"name":"Barcode"},{"name":"Glyph"}]} */
(function () {
  "use strict";
  var React = window.React;
  var h = React.createElement;

  function cx() {
    var out = [];
    for (var i = 0; i < arguments.length; i++) { if (arguments[i]) out.push(arguments[i]); }
    return out.join(" ");
  }

  /* ---------- Glyph: marcas de instrumento en rejilla de 24 ---------- */
  var GLYPHS = {
    plus:         { p: ["M12 3V9M12 15V21M3 12H9M15 12H21"], w: 1.5 },
    close:        { p: ["M6 6L10 10M14 14L18 18M18 6L14 10M10 14L6 18"], w: 1.5 },
    "tick-left":  { p: ["M5 3V21M5 12H20"], w: 1.5 },
    "tick-right": { p: ["M19 3V21M19 12H4"], w: 1.5 },
    bracket:      { p: ["M3 9V3H9M15 3H21V9M21 15V21H15M9 21H3V15"], w: 2 },
    corner:       { p: ["M4 21V9L9 4H21"], w: 1.5 },
    slash:        { p: ["M4 20L20 4"], w: 3.5 },
    "slash-pair": { p: ["M2 16L14 4M10 20L22 8"], w: 3.5 },
    "chevron-down":  { p: ["M4 8L12 16L20 8"], w: 3 },
    "chevron-right": { p: ["M8 4L16 12L8 20"], w: 3 },
    dots:         { r: [[3, 11, 2], [11, 11, 2], [19, 11, 2]] },
    dot:          { r: [[10, 10, 4]] }
  };

  function Glyph(props) {
    var def = GLYPHS[props.name] || GLYPHS.plus;
    var size = props.size || 24;
    var nodes = [];
    (def.p || []).forEach(function (d, i) {
      nodes.push(h("path", { key: "p" + i, d: d, fill: "none", stroke: "currentColor", strokeWidth: def.w, strokeLinecap: "butt", strokeLinejoin: "miter" }));
    });
    (def.r || []).forEach(function (r, i) {
      nodes.push(h("rect", { key: "r" + i, x: r[0], y: r[1], width: r[2], height: r[2], fill: "currentColor" }));
    });
    return h("svg", {
      className: cx("tm-glyph", "tm-tone-" + (props.tone || "ink"), props.className),
      width: size, height: size, viewBox: "0 0 24 24",
      role: props.label ? "img" : undefined,
      "aria-label": props.label || undefined,
      "aria-hidden": props.label ? undefined : "true",
      focusable: "false", style: props.style
    }, nodes);
  }

  /* ---------- Hazard: rayas de peligro ---------- */
  function Hazard(props) {
    return h("div", {
      className: cx("tm-hazard", props.tone === "signal" && "tm-hazard--signal", props.className),
      style: Object.assign({}, props.height ? { height: props.height } : null, props.width ? { width: props.width } : null, props.style),
      "aria-hidden": "true"
    });
  }

  /* ---------- DotGrid: retícula de puntos ---------- */
  function DotGrid(props) {
    var cols = props.cols || 12, rows = props.rows || 3, pitch = 16, d = "";
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) { d += "M" + (c * pitch) + " " + (r * pitch) + "h4v4h-4z"; }
    }
    return h("div", { className: cx("tm-dotgrid", props.className), style: props.style, "aria-hidden": "true" },
      props.lead ? h("span", { className: "tm-dotgrid__lead" }) : null,
      h("svg", {
        className: cx("tm-dotgrid__svg", "tm-dotgrid--" + (props.tone || "graphite")),
        width: cols * pitch - 12, height: rows * pitch - 12, viewBox: "0 0 " + (cols * pitch - 12) + " " + (rows * pitch - 12),
        focusable: "false"
      }, h("path", { d: d, fill: "currentColor" }))
    );
  }

  /* ---------- Barcode: barra modular de segmentos ---------- */
  var PATTERN = [10, 3, 3, 3, 2, 5, 2, 2, 6, 2, 3, 8, 2, 2, 4, 3, 12, 2, 2, 3, 6, 2, 3, 3, 2];
  function Barcode(props) {
    var seg = props.segments || PATTERN;
    return h("div", {
      className: cx("tm-barcode", "tm-barcode--" + (props.tone || "signal"), props.className),
      style: props.style, "aria-hidden": "true"
    }, seg.map(function (w, i) {
      return h("i", { key: i, className: i % 2 === 0 ? "on" : "", style: { flexGrow: w } });
    }));
  }

  /* ---------- Tag ---------- */
  function Tag(props) {
    var text = props.bracket ? "[ " + props.children + " ]" : props.children;
    return h("span", { className: cx("tm-tag", "tm-tag--" + (props.tone || "graphite"), props.className), style: props.style }, text);
  }

  /* ---------- Button ---------- */
  function Button(props) {
    var variant = props.variant || "primary";
    return h("button", {
      type: props.type || "button",
      className: cx("tm-btn", "tm-btn--" + variant, "tm-focusable", props.className),
      disabled: props.disabled, onClick: props.onClick, style: props.style
    }, props.children, props.arrow ? h(Glyph, { name: "chevron-right", size: 16 }) : null);
  }

  /* ---------- IconButton ---------- */
  function IconButton(props) {
    var glyph = props.glyph || "plus";
    var btn = h("button", {
      type: "button",
      className: cx("tm-ibtn", "tm-focusable", props.className),
      "aria-label": props.label,
      "aria-pressed": props.pressed === undefined ? undefined : String(!!props.pressed),
      disabled: props.disabled, onClick: props.onClick, style: props.style
    }, h(Glyph, { name: glyph, size: 20 }));
    if (!props.pressed) return btn;
    return h("span", { className: "tm-ibtn-wrap" }, btn, h(Glyph, { name: "tick-left", size: 16, tone: "signal" }));
  }

  /* ---------- Progress ---------- */
  function Progress(props) {
    var v = Math.max(0, Math.min(1, props.value || 0));
    var pct = Math.round(v * 100);
    return h("div", { className: cx("tm-progress", props.className), style: props.style },
      h("div", { className: "tm-progress__row label" },
        h("span", null, props.label),
        h("span", { className: "tm-progress__pct" }, pct + "%")),
      h("div", { className: "tm-progress__bar" },
        h("div", { className: "tm-progress__track", role: "progressbar", "aria-label": props.label, "aria-valuemin": 0, "aria-valuemax": 100, "aria-valuenow": pct },
          h("span", { className: "tm-progress__fill", style: { width: "calc((100% - 4px) * " + v + ")" } })),
        props.hazard === false ? null : h(Hazard, { className: "tm-progress__hazard" })));
  }

  /* ---------- Readout ---------- */
  function Readout(props) {
    return h("div", { className: cx("tm-readout", props.className), style: props.style },
      props.title ? h("p", { className: "label tm-readout__title" }, props.title) : null,
      h("dl", { className: "tm-readout__list" }, (props.items || []).map(function (it, i) {
        return h("div", { key: i, className: "tm-readout__row" },
          h("dt", { className: "label" }, it.label),
          h("dd", { className: "label" }, it.status ? h(Tag, { tone: it.tone || "graphite" }, it.value) : it.value));
      })));
  }

  /* ---------- Headline ---------- */
  var SIZES = { lg: "display-a", md: "display-c", sm: "headline" };
  function Headline(props) {
    var Tagname = props.as || "h2";
    return h("header", { className: cx("tm-headline", props.className), style: props.style },
      h("span", { className: cx("tm-headline__rule", props.rule === "graphite" && "tm-headline__rule--graphite"), "aria-hidden": "true" }),
      props.kicker ? h("p", { className: "label tm-headline__kicker" }, props.kicker) : null,
      h(Tagname, { className: cx("tm-headline__title", SIZES[props.size || "md"]) }, props.title),
      props.subtitle ? h("p", { className: "byline tm-headline__subtitle" }, props.subtitle) : null,
      props.by ? h("p", { className: "byline tm-headline__by" }, props.by) : null);
  }

  /* ---------- Frame: marco de imagen pendiente ---------- */
  function Frame(props) {
    return h("figure", { className: cx("tm-frame", props.className), style: props.style },
      h("div", { className: "tm-frame__box", role: "img", "aria-label": props.label || "Imagen pendiente", style: { aspectRatio: props.ratio || "16 / 9" } },
        h("svg", { className: "tm-frame__x", viewBox: "0 0 100 100", preserveAspectRatio: "none", focusable: "false", "aria-hidden": "true" },
          h("path", { d: "M0 0L100 100M100 0L0 100", fill: "none", stroke: "currentColor", strokeWidth: 1, vectorEffect: "non-scaling-stroke" }))),
      props.caption ? h("figcaption", { className: "label tm-frame__caption" }, props.caption) : null);
  }

  /* ---------- Panel ---------- */
  function Marks() {
    return h("svg", { className: "tm-panel__marks", width: 36, height: 20, viewBox: "0 0 36 20", "aria-hidden": "true", focusable: "false" },
      h("rect", { x: 0, y: 0, width: 4, height: 4, fill: "currentColor" }),
      h("rect", { x: 16, y: 0, width: 4, height: 4, fill: "currentColor" }),
      h("rect", { x: 0, y: 16, width: 4, height: 4, fill: "currentColor" }),
      h("rect", { x: 32, y: 16, width: 4, height: 4, fill: "currentColor" }));
  }
  function Panel(props) {
    var tone = props.tone || "raised";
    var chamfer = props.chamfer !== false;
    var hasHead = props.label || props.note;
    var hasFoot = props.code || props.marks;
    return h("section", { className: cx("tm-panel", "tm-panel--" + tone, chamfer && "tm-panel--chamfer", props.className), style: props.style },
      hasHead ? h("header", { className: "tm-panel__head" },
        props.label ? h("p", { className: "label tm-panel__label" }, props.label) : null,
        props.note ? h("p", { className: "label tm-panel__note" }, props.note) : null) : null,
      props.children ? h("div", { className: "tm-panel__body" }, props.children) : null,
      hasFoot ? h("footer", { className: "tm-panel__foot" },
        props.code ? h("p", { className: "code tm-panel__code" }, props.code) : h("span"),
        props.marks ? h(Marks) : null) : null);
  }

  window.Reticula = {
    Panel: Panel, Tag: Tag, Button: Button, IconButton: IconButton, Progress: Progress,
    Readout: Readout, Headline: Headline, Frame: Frame, Hazard: Hazard, DotGrid: DotGrid,
    Barcode: Barcode, Glyph: Glyph
  };
})();
