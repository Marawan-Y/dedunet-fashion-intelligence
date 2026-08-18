module.exports = ({ config }) => {
  const allowLocalHttp =
    process.env.DEDUNET_ALLOW_LOCAL_HTTP === "true";

  // Remove managed plugins first so repeated config evaluation
  // can never register either plugin twice.
  const plugins = (config.plugins ?? []).filter((plugin) => {
    const name = Array.isArray(plugin) ? plugin[0] : plugin;

    return (
      name !== "expo-build-properties" &&
      name !== "expo-image"
    );
  });

  // Required by the native gallery.
  plugins.push("expo-image");

  // Local emulator/staging only.
  if (allowLocalHttp) {
    plugins.push([
      "expo-build-properties",
      {
        android: {
          usesCleartextTraffic: true,
        },
      },
    ]);
  }

  return {
    ...config,
    plugins,
  };
};