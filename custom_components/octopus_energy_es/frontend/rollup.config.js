import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import terser from '@rollup/plugin-terser';

export default {
  input: 'dist/octopus-consumption-card.js',
  output: {
    file: 'dist/octopus-consumption-card.bundle.js',
    format: 'iife',
    name: 'OctopusConsumptionCard',
    sourcemap: false  // Disable source maps for production builds
  },
  plugins: [
    resolve({
      browser: true,
      preferBuiltins: false
    }),
    commonjs(),
    terser({
      compress: {
        drop_console: false
      }
    })
  ]
};
