/**
 * Entry point.
 *
 * `registerRootComponent` replaces the SDK-45-era `main: node_modules/expo/AppEntry.js`
 * that the previous package.json pointed at. That path reaches inside a dependency, which
 * breaks whenever the dependency reorganises its files, and it is no longer how Expo
 * projects are entered.
 */

import { registerRootComponent } from "expo";

import App from "./App";

registerRootComponent(App);
