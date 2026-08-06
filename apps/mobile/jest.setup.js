/**
 * Jest environment setup.
 *
 * AsyncStorage is a native module with no implementation under Node, so it must be
 * replaced by the mock the package ships. Without this every test that touches storage
 * fails with "NativeModule: AsyncStorage is null" -- which looks like a bug in the code
 * under test rather than a missing test harness.
 */

// eslint-disable-next-line @typescript-eslint/no-require-imports
jest.mock("@react-native-async-storage/async-storage", () =>
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  require("@react-native-async-storage/async-storage/jest/async-storage-mock")
);
