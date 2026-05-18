module.exports = function (api) {
  api.cache(true);

  // nativewind/babel → react-native-css-interop/babel, which already ends with
  // react-native-worklets/plugin (required for Reanimated 4). Do NOT also add
  // react-native-reanimated/plugin — it re-exports the same worklets plugin.
  const nativewindBabel = require('nativewind/babel');
  const nativewindPlugins =
    typeof nativewindBabel === 'function' ? nativewindBabel().plugins : [];

  return {
    presets: ['babel-preset-expo'],
    plugins: [...nativewindPlugins],
  };
};
