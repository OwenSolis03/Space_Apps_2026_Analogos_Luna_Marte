const fs = require('fs');
const path = require('path');

const svgDir = path.resolve('PROTOTERRA-logos', 'svg');

// Text path for horizontal layout (from 05-imagotipo-horizontal.svg)
const textHorizontal = `<path d="M628.36 265V213.8H645.39Q650.19 213.8 653.74 215.62Q657.29 217.45 659.24 220.78Q661.19 224.1 661.19 228.71Q661.19 233.19 659.24 236.52Q657.29 239.85 653.74 241.67Q650.19 243.5 645.39 243.5H634.76V265ZM634.76 237.8H645.64Q649.93 237.8 652.36 235.4Q654.79 233 654.79 228.78Q654.79 224.55 652.36 222.15Q649.93 219.75 645.64 219.75H634.76ZM679.82 265V213.8H696.52Q701.45 213.8 705.07 215.56Q708.68 217.32 710.7 220.62Q712.71 223.91 712.71 228.46Q712.71 232.74 710.7 235.94Q708.68 239.14 705.03 240.94Q702.73 242.09 699.91 242.47L713.8 265H706.57L693.19 242.73H686.22V265ZM686.22 237.22H696.71Q701.13 237.22 703.72 234.86Q706.31 232.49 706.31 228.52Q706.31 224.49 703.72 222.12Q701.13 219.75 696.71 219.75H686.22ZM746.95 265.96Q737.87 265.96 733.29 259.34Q728.71 252.71 728.71 239.4Q728.71 226.09 733.26 219.46Q737.8 212.84 746.95 212.84Q756.04 212.84 760.62 219.46Q765.19 226.09 765.19 239.4Q765.19 252.71 760.65 259.34Q756.11 265.96 746.95 265.96ZM746.95 260.01Q753.03 260.01 755.95 254.98Q758.86 249.96 758.86 239.4Q758.86 228.84 755.95 223.82Q753.03 218.79 746.95 218.79Q740.87 218.79 737.96 223.82Q735.05 228.84 735.05 239.4Q735.05 249.96 737.96 254.98Q740.87 260.01 746.95 260.01ZM796.23 265V219.75H781.07V213.8H817.8V219.75H802.63V265ZM851.91 265.96Q842.83 265.96 838.25 259.34Q833.67 252.71 833.67 239.4Q833.67 226.09 838.22 219.46Q842.76 212.84 851.91 212.84Q861 212.84 865.58 219.46Q870.15 226.09 870.15 239.4Q870.15 252.71 865.61 259.34Q861.07 265.96 851.91 265.96ZM851.91 260.01Q857.99 260.01 860.91 254.98Q863.82 249.96 863.82 239.4Q863.82 228.84 860.91 223.82Q857.99 218.79 851.91 218.79Q845.83 218.79 842.92 223.82Q840.01 228.84 840.01 239.4Q840.01 249.96 842.92 254.98Q845.83 260.01 851.91 260.01ZM901.19 265V219.75H886.03V213.8H922.76V219.75H907.59V265ZM944.01 265V213.8H973.45V219.75H950.35V236.39H970.25V242.02H950.35V259.05H972.81V265ZM994.7 265V213.8H1011.4Q1016.33 213.8 1019.95 215.56Q1023.56 217.32 1025.58 220.62Q1027.59 223.91 1027.59 228.46Q1027.59 232.74 1025.58 235.94Q1023.56 239.14 1019.91 240.94Q1017.61 242.09 1014.79 242.47L1028.68 265H1021.45L1008.07 242.73H1001.1V265ZM1001.1 237.22H1011.59Q1016.01 237.22 1018.6 234.86Q1021.19 232.49 1021.19 228.52Q1021.19 224.49 1018.6 222.12Q1016.01 219.75 1011.59 219.75H1001.1ZM1047.18 265V213.8H1063.88Q1068.81 213.8 1072.43 215.56Q1076.04 217.32 1078.06 220.62Q1080.07 223.91 1080.07 228.46Q1080.07 232.74 1078.06 235.94Q1076.04 239.14 1072.39 240.94Q1070.09 242.09 1067.27 242.47L1081.16 265H1073.93L1060.55 242.73H1053.58V265ZM1053.58 237.22H1064.07Q1068.49 237.22 1071.08 234.86Q1073.67 232.49 1073.67 228.52Q1073.67 224.49 1071.08 222.12Q1068.49 219.75 1064.07 219.75H1053.58ZM1095.69 265 1109.13 213.8H1119.5L1132.94 265H1126.28L1121.67 246.95H1106.57L1101.96 265ZM1120.14 240.94 1114.44 218.66H1113.87L1108.17 240.94Z" fill="#121212"/>`;

// Text path for vertical layout (from 07-imagotipo-vertical.svg)
const textVertical = `<path d="M186.36 549.5V498.3H203.39Q208.19 498.3 211.74 500.12Q215.29 501.95 217.24 505.28Q219.19 508.6 219.19 513.21Q219.19 517.69 217.24 521.02Q215.29 524.35 211.74 526.17Q208.19 528 203.39 528H192.76V549.5ZM192.76 522.3H203.64Q207.93 522.3 210.36 519.9Q212.79 517.5 212.79 513.28Q212.79 509.05 210.36 506.65Q207.93 504.25 203.64 504.25H192.76ZM237.82 549.5V498.3H254.52Q259.45 498.3 263.07 500.06Q266.68 501.82 268.7 505.12Q270.71 508.41 270.71 512.96Q270.71 517.24 268.7 520.44Q266.68 523.64 263.03 525.44Q260.73 526.59 257.91 526.97L271.8 549.5H264.57L251.19 527.23H244.22V549.5ZM244.22 521.72H254.71Q259.13 521.72 261.72 519.36Q264.31 516.99 264.31 513.02Q264.31 508.99 261.72 506.62Q259.13 504.25 254.71 504.25H244.22ZM304.95 550.46Q295.87 550.46 291.29 543.84Q286.71 537.21 286.71 523.9Q286.71 510.59 291.26 503.96Q295.8 497.34 304.95 497.34Q314.04 497.34 318.62 503.96Q323.19 510.59 323.19 523.9Q323.19 537.21 318.65 543.84Q314.11 550.46 304.95 550.46ZM304.95 544.51Q311.03 544.51 313.95 539.48Q316.86 534.46 316.86 523.9Q316.86 513.34 313.95 508.32Q311.03 503.29 304.95 503.29Q298.87 503.29 295.96 508.32Q293.05 513.34 293.05 523.9Q293.05 534.46 295.96 539.48Q298.87 544.51 304.95 544.51ZM354.23 549.5V504.25H339.07V498.3H375.8V504.25H360.63V549.5ZM409.91 550.46Q400.83 550.46 396.25 543.84Q391.67 537.21 391.67 523.9Q391.67 510.59 396.22 503.96Q400.76 497.34 409.91 497.34Q419 497.34 423.58 503.96Q428.15 510.59 428.15 523.9Q428.15 537.21 423.61 543.84Q419.07 550.46 409.91 550.46ZM409.91 544.51Q415.99 544.51 418.91 539.48Q421.82 534.46 421.82 523.9Q421.82 513.34 418.91 508.32Q415.99 503.29 409.91 503.29Q403.83 503.29 400.92 508.32Q398.01 513.34 398.01 523.9Q398.01 534.46 400.92 539.48Q403.83 544.51 409.91 544.51ZM459.19 549.5V504.25H444.03V498.3H480.76V504.25H465.59V549.5ZM502.01 549.5V498.3H531.45V504.25H508.35V520.89H528.25V526.52H508.35V543.55H530.81V549.5ZM552.7 549.5V498.3H569.4Q574.33 498.3 577.95 500.06Q581.56 501.82 583.58 505.12Q585.59 508.41 585.59 512.96Q585.59 517.24 583.58 520.44Q581.56 523.64 577.91 525.44Q575.61 526.59 572.79 526.97L586.68 549.5H579.45L566.07 527.23H559.1V549.5ZM559.1 521.72H569.59Q574.01 521.72 576.6 519.36Q579.19 516.99 579.19 513.02Q579.19 508.99 576.6 506.62Q574.01 504.25 569.59 504.25H559.1ZM605.18 549.5V498.3H621.88Q626.81 498.3 630.43 500.06Q634.04 501.82 636.06 505.12Q638.07 508.41 638.07 512.96Q638.07 517.24 636.06 520.44Q634.04 523.64 630.39 525.44Q628.09 526.59 625.27 526.97L639.16 549.5H631.93L618.55 527.23H611.58V549.5ZM611.58 521.72H622.07Q626.49 521.72 629.08 519.36Q631.67 516.99 631.67 513.02Q631.67 508.99 629.08 506.62Q626.49 504.25 622.07 504.25H611.58ZM653.69 549.5 667.13 498.3H677.5L690.94 549.5H684.28L679.67 531.45H664.57L659.96 549.5ZM678.14 525.44 672.44 503.16H671.87L666.17 525.44Z" fill="#121212"/>`;

function buildIconSvg(x, y, w, h, bg, idPrefix) {
  return `<svg x="${x}" y="${y}" width="${w}" height="${h}" viewBox="0 -32 560 304">
<defs>
<pattern id="${idPrefix}-odots" width="16" height="16" patternUnits="userSpaceOnUse" x="6" y="6"><rect width="4" height="4" fill="none"></rect></pattern>
<pattern id="${idPrefix}-mdots" width="16" height="16" patternUnits="userSpaceOnUse" x="6" y="6"><rect width="4" height="4" fill="#121212"></rect></pattern>
<pattern id="${idPrefix}-hatch" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="3" height="12" fill="#121212"></rect></pattern>
<clipPath id="${idPrefix}-earth"><circle cx="280" cy="120" r="103"></circle></clipPath>
</defs>
<circle cx="280" cy="120" r="128" fill="none" stroke="#121212" stroke-width="1.5"></circle>
<rect x="276" y="-12" width="8" height="8" fill="#121212"></rect>
<path d="M280 236 L280 241 M280 247 L280 252 M272 244 L277 244 M283 244 L288 244" stroke="#121212" stroke-width="1.5" fill="none"></path>
<circle cx="280" cy="120" r="103" fill="${bg}" stroke="#121212" stroke-width="2"></circle>
<path d="M232 22 L300 18 L318 34 L300 48 L292 62 L280 70 L272 84 L262 96 L268 104 L276 118 L284 128 L296 132 L318 140 L330 152 L326 172 L312 190 L302 210 L296 224 L290 214 L288 190 L282 168 L276 150 L270 138 L262 124 L254 110 L246 96 L236 78 L226 60 L220 40 Z" fill="#121212" clip-path="url(#${idPrefix}-earth)"></path>
<circle cx="152" cy="120" r="110" fill="${bg}"></circle>
<circle cx="152" cy="120" r="103" fill="${bg}" stroke="#121212" stroke-width="2"></circle>
<circle cx="152" cy="120" r="101" fill="url(#${idPrefix}-mdots)"></circle>
<circle cx="408" cy="120" r="110" fill="${bg}"></circle>
<circle cx="408" cy="120" r="103" fill="${bg}" stroke="#121212" stroke-width="2"></circle>
<circle cx="408" cy="120" r="101" fill="url(#${idPrefix}-hatch)"></circle>
</svg>`;
}

// 1. Symbol White Background (03-logo-una-tinta-fondo-blanco.svg)
const logoSymbolWhite = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 560" width="880" height="560" role="img" aria-label="PROTOTERRA">
<rect width="880" height="560" fill="#ffffff"/>
${buildIconSvg(140.0, 117.0, 600, 326, '#ffffff', 'mono-w-sym')}
</svg>`;
fs.writeFileSync(path.join(svgDir, '03-logo-una-tinta-fondo-blanco.svg'), logoSymbolWhite, 'utf8');

// 2. Imagotipo Horizontal Una Tinta (Gris) (08-imagotipo-horizontal-una-tinta.svg)
const imagotipoHorizGris = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 480" width="1280" height="480" role="img" aria-label="PROTOTERRA">
<rect width="1280" height="480" fill="#dfdfdf"/>
${buildIconSvg(135.59, 131.5, 400, 217, '#dfdfdf', 'mono-h-gris')}
<rect x="575.59" y="208.00" width="4.00" height="64.00" fill="#121212"/>
${textHorizontal}
</svg>`;
fs.writeFileSync(path.join(svgDir, '08-imagotipo-horizontal-una-tinta.svg'), imagotipoHorizGris, 'utf8');

// 3. Imagotipo Horizontal Una Tinta (Fondo Blanco) (08-imagotipo-horizontal-una-tinta-fondo-blanco.svg)
const imagotipoHorizWhite = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 480" width="1280" height="480" role="img" aria-label="PROTOTERRA">
<rect width="1280" height="480" fill="#ffffff"/>
${buildIconSvg(135.59, 131.5, 400, 217, '#ffffff', 'mono-h-white')}
<rect x="575.59" y="208.00" width="4.00" height="64.00" fill="#121212"/>
${textHorizontal}
</svg>`;
fs.writeFileSync(path.join(svgDir, '08-imagotipo-horizontal-una-tinta-fondo-blanco.svg'), imagotipoHorizWhite, 'utf8');

// 4. Imagotipo Vertical Una Tinta (Gris) (09-imagotipo-vertical-una-tinta.svg)
const imagotipoVertGris = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 720" width="880" height="720" role="img" aria-label="PROTOTERRA">
<rect width="880" height="720" fill="#dfdfdf"/>
${buildIconSvg(200, 163.5, 480, 261, '#dfdfdf', 'mono-v-gris')}
<rect x="408.00" y="472.50" width="64.00" height="4.00" fill="#121212"/>
${textVertical}
</svg>`;
fs.writeFileSync(path.join(svgDir, '09-imagotipo-vertical-una-tinta.svg'), imagotipoVertGris, 'utf8');

// 5. Imagotipo Vertical Una Tinta (Fondo Blanco) (09-imagotipo-vertical-una-tinta-fondo-blanco.svg)
const imagotipoVertWhite = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 720" width="880" height="720" role="img" aria-label="PROTOTERRA">
<rect width="880" height="720" fill="#ffffff"/>
${buildIconSvg(200, 163.5, 480, 261, '#ffffff', 'mono-v-white')}
<rect x="408.00" y="472.50" width="64.00" height="4.00" fill="#121212"/>
${textVertical}
</svg>`;
fs.writeFileSync(path.join(svgDir, '09-imagotipo-vertical-una-tinta-fondo-blanco.svg'), imagotipoVertWhite, 'utf8');

console.log('Successfully generated Canva single-ink SVGs in', svgDir);
