# Troubleshooting GraalVM Native Image

## Overview

Use this skill to route Native Image build and runtime failures to the smallest relevant fix. Use [reachability-metadata.md](reachability-metadata.md) for missing reflection, JNI, proxy, resource, bundle, or serialization metadata.

## Missing Reachability Metadata

If you encounter runtime errors related to reflection, JNI, resources, serialization, or dynamic proxies, consult [reachability-metadata.md](reachability-metadata.md) before attempting a fix.

Use that file for:

- `NoClassDefFoundError` or `MissingReflectionRegistrationError`
- `MissingJNIRegistrationError`
- `MissingResourceException` from a missing resource bundle
- Any user question about reflection, JNI, proxies, resources, resource bundles, or serialization in Native Image

For exact error reporting with GraalVM JDK 23+:

```bash
native-image --exact-reachability-metadata <class>
```

For scoped exact metadata handling:

```bash
native-image --exact-reachability-metadata-path=<path> <class>
```

Run the app with warning mode to see missing registrations without crashing:

```shell
java -XX:MissingRegistrationReportingMode=Warn -jar your-app.jar
```

Use `Exit` mode during testing to catch errors hidden inside `catch (Throwable t)` blocks:

```shell
java -XX:MissingRegistrationReportingMode=Exit -jar your-app.jar
```

For GraalVM versions prior to JDK 23, use the build-time options `-H:ThrowMissingRegistrationErrors=` and `-H:MissingRegistrationReportingMode=Warn` instead.

It is not always necessary to add all reported elements to `reachability-metadata.json`. The element causing the program failure is usually among the last listed.

## Classpath and Modules

If `native-image` cannot find your classes:

```bash
native-image -cp <path1>:<path2> <class>
```

If using modules:

```bash
native-image -p <module-path> --add-modules <module-name> <class>
```

## Class Initialization and Linking

If a class fails because it initializes at build time but must not:

```bash
native-image --initialize-at-run-time=com.example.LazyClass <class>
```

If a class must be initialized at build time:

```bash
native-image --initialize-at-build-time=com.example.EagerClass <class>
```

If a type must be fully defined at build time:

```bash
native-image --link-at-build-time <class>
```

## Builder JVM and Memory

If the build runs out of memory:

```bash
native-image -J-Xmx8g <class>
```

If you need to set a system property at build time:

```bash
native-image -Dkey=value <class>
```

If you need to pass a flag to the JVM running the builder:

```bash
native-image -J<flag> <class>
```

## Diagnostics

If you want debug symbols in the binary:

```bash
native-image -g <class>
```

If you want verbose build output:

```bash
native-image --verbose <class>
```

If you want to inspect class initialization and substitutions:

```bash
native-image --diagnostics-mode <class>
```

If you want a detailed HTML build report:

```bash
native-image --emit build-report <class>
# or: --emit build-report=report.html
```

If you want to trace instantiation of a specific class:

```bash
native-image --trace-object-instantiation=com.example.MyClass <class>
```

If you want to see the native toolchain and build settings:

```bash
native-image --native-image-info
```

## Maven Native Build Tools

- `"Could not resolve artifact"` - Ensure `mavenCentral()` is in repositories and the version is correct.
- `"Could not find goal 'compile-no-fork'"` - Verify `<extensions>true</extensions>` is set on the plugin.
- Build runs without native compilation - Check you are activating the profile: `./mvnw -Pnative package`.
- `"No tests found" in native test` - Ensure you declare `maven-surefire-plugin` 3.0+ in your build. If you use Maven Surefire prior to 3.0 M4 or your build forces an older JUnit Platform version, add `junit-platform-launcher` to test dependencies.

If Maven native tests fail due to missing reflection or resource metadata, collect metadata using the tracing agent:

```bash
./mvnw -Pnative -Dagent=true test
./mvnw -Pnative native:metadata-copy
./mvnw -Pnative test
```

## Gradle Native Build Tools

If the build fails with class initialization, linking errors, memory issues, or the binary behaves incorrectly at runtime, configure the relevant `buildArgs`, `jvmArgs`, or diagnostics in the `graalvmNative` block. See [native-build-tools.md](native-build-tools.md).

If Gradle native tests fail and you need the native test binary, the source location is:

```text
build/native/nativeTestCompile/<imageName>
```

## Additional Run-Time Checks

Sometimes upgrading to the latest GraalVM version can resolve a run-time issue.

If the application code uses the `java.home` property, set it explicitly when running the native executable. Otherwise, `System.getProperty("java.home")` returns `null`.

```bash
./myapp -Djava.home=<path>
```

For URL protocol support, see [build-native-image.md](build-native-image.md). If the failure involves charset-sensitive behavior, add charset support at build time. This can increase binary size.

```bash
native-image -H:+AddAllCharsets <class>
```

For locale-sensitive resource bundle behavior, see [reachability-metadata.md](reachability-metadata.md). If the application uses security providers, pre-initialize them at build time:

```bash
native-image -H:AdditionalSecurityProviders=<list-of-providers> <class>
```

For diagnosing native shared libraries, use missing-registration exit mode:

```bash
native-image -R:MissingRegistrationReportingMode=Exit <class>
```

## Sources

- https://github.com/oracle/graal/tree/master/substratevm/skills/building-native-image
- https://github.com/oracle/graal/tree/master/substratevm/skills/build-native-image-maven
- https://github.com/oracle/graal/tree/master/substratevm/skills/build-native-image-gradle
- https://www.graalvm.org/jdk25/reference-manual/native-image/guides/troubleshoot-run-time-errors/
