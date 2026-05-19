# GraalVM Native Build Tools

## Overview

Use this skill to build GraalVM native images with Maven or Gradle. Use [build-native-image.md](build-native-image.md) for raw `native-image` flags and [reachability-metadata.md](reachability-metadata.md) for manual metadata JSON.

## Maven Native Image Build

### Prerequisites

- Set `JAVA_HOME` to a GraalVM JDK installation so the plugin can find `native-image`.
- Do not require `GRAALVM_HOME` in the normal case. Only mention it if the user already relies on it or their environment needs an explicit override.
- Use Maven 3.6+.

### Plugin Setup

Add the following to `pom.xml`:

```xml
<profiles>
  <profile>
    <id>native</id>
    <build>
      <plugins>
        <plugin>
          <groupId>org.graalvm.buildtools</groupId>
          <artifactId>native-maven-plugin</artifactId>
          <version>0.11.1</version>
          <extensions>true</extensions>
          <executions>
            <execution>
              <id>build-native</id>
              <goals>
                <goal>compile-no-fork</goal>
              </goals>
              <phase>package</phase>
            </execution>
            <execution>
              <id>test-native</id>
              <goals>
                <goal>test</goal>
              </goals>
              <phase>test</phase>
            </execution>
          </executions>
          <configuration>
            <mainClass>org.example.Main</mainClass>
          </configuration>
        </plugin>
      </plugins>
    </build>
  </profile>
</profiles>
```

### Build and Run

```bash
./mvnw -Pnative package                    # Build native image to target/<imageName>
./target/myapp                             # Run the native executable
./mvnw -Pnative test                       # Build and run JUnit tests as a native image
./mvnw -Pnative -DskipTests package        # Skip all tests
./mvnw -Pnative -DskipNativeTests package  # Run JVM tests only, skip native
```

### Maven Configuration Options

| Option | Type | Default | Purpose |
|--------|------|---------|---------|
| `<imageName>` | String | artifactId | Name of the output executable |
| `<mainClass>` | String | none | Entry point class (required) |
| `<debug>` | boolean | `false` | Generate debug info |
| `<verbose>` | boolean | `false` | Enable verbose build output |
| `<fallback>` | boolean | `false` | Allow fallback to JVM |
| `<sharedLibrary>` | boolean | `false` | Build shared library instead of executable |
| `<quickBuild>` | boolean | `false` | Faster build, lower runtime performance |
| `<useArgFile>` | boolean | `true` | Use argument file for long classpaths |
| `<skipNativeBuild>` | boolean | `false` | Skip native compilation |
| `<skipNativeTests>` | boolean | `false` | Skip native test execution |
| `<buildArgs>` | List | empty | Arguments passed directly to `native-image` |
| `<jvmArgs>` | List | empty | JVM arguments for the native-image builder |
| `<runtimeArgs>` | List | empty | Arguments passed to the app at runtime |
| `<environment>` | Map | empty | Environment variables during build |
| `<systemPropertyVariables>` | Map | empty | System properties during build |
| `<classpath>` | List | auto | Override classpath entries |
| `<classesDirectory>` | String | auto | Override classes directory |

Pass any `native-image` flag via `<buildArgs>`:

```xml
<buildArgs>
  <buildArg>--initialize-at-run-time=com.example.LazyClass</buildArg>
  <buildArg>-H:IncludeResources=.*\.xml$</buildArg>
  <buildArg>-O2</buildArg>
</buildArgs>
```

If the build runs out of memory:

```xml
<jvmArgs>
  <arg>-Xmx8g</arg>
</jvmArgs>
```

Child projects can append build arguments to a parent POM config using `combine.children`:

```xml
<buildArgs combine.children="append">
  <buildArg>--verbose</buildArg>
</buildArgs>
```

If using `maven-shade-plugin`, point the native plugin to the shaded JAR:

```xml
<configuration>
  <useArgFile>false</useArgFile>
  <classpath>
    <param>${project.build.directory}/${project.artifactId}-${project.version}-shaded.jar</param>
  </classpath>
</configuration>
```

### Maven Plugin Not Resolving or Activating

- `"Could not resolve artifact"` - Ensure `mavenCentral()` is in repositories and the version is correct.
- `"Could not find goal 'compile-no-fork'"` - Verify `<extensions>true</extensions>` is set on the plugin.
- Build runs without native compilation - Check you are activating the profile: `./mvnw -Pnative package`.

## Gradle Native Image Build

### Prerequisites

- Set `JAVA_HOME` to a GraalVM JDK installation so Gradle Native Build Tools can find `native-image`.
- Do not require `GRAALVM_HOME` in the normal case. Only mention it if the user already relies on it or their environment needs an explicit override.
- Apply the `application`, `java-library`, or `java` plugin along with `org.graalvm.buildtools.native`.

### Plugin Setup

Groovy DSL:

```groovy
plugins {
    id 'application'
    id 'org.graalvm.buildtools.native' version '0.11.1'
}
```

Kotlin DSL:

```kotlin
plugins {
    application
    id("org.graalvm.buildtools.native") version "0.11.1"
}
```

### Build and Run

```bash
./gradlew nativeCompile   # Build to build/native/nativeCompile/
./gradlew nativeRun       # Build and run the native executable
./gradlew nativeTest      # Build and run JUnit tests as a native image
```

### Gradle DSL Structure

```groovy
graalvmNative {
    binaries {
        main { /* application binary options */ }
        test { /* test binary options */ }
        all  { /* shared options */ }
    }
}
```

### Gradle Binary Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `imageName` | String | project name | Output executable name |
| `mainClass` | String | `application.mainClass` | Main entry point class |
| `debug` | boolean | `false` | Enable debug info, or use `--debug-native` |
| `verbose` | boolean | `false` | Verbose build output |
| `sharedLibrary` | boolean | `false` | Build a shared library |
| `quickBuild` | boolean | `false` | Faster build, lower runtime performance |
| `richOutput` | boolean | `false` | Rich console output |
| `jvmArgs` | ListProperty | empty | JVM arguments for native-image builder |
| `buildArgs` | ListProperty | empty | Arguments for native-image |
| `runtimeArgs` | ListProperty | empty | Arguments for the application at runtime |
| `javaLauncher` | Property | auto-detected | GraalVM toolchain launcher |

### Gradle Binary Configuration

Rename the output binary:

```groovy
imageName = 'myapp'
```

Set the entry point:

```groovy
mainClass = 'com.example.Main'
```

Enable debug info:

```groovy
debug = true
// or use --debug-native
```

Verbose build output:

```groovy
verbose = true
```

Faster builds during development:

```groovy
quickBuild = true
// or use -Ob buildArg for maximum speed
buildArgs.add('-Ob')
```

Build a shared library instead of an executable:

```groovy
sharedLibrary = true
```

Increase build memory:

```groovy
jvmArgs.add('-Xmx8g')
```

Force runtime initialization for a class:

```groovy
buildArgs.add('--initialize-at-run-time=com.example.LazyClass')
```

Force build-time initialization for a class:

```groovy
buildArgs.add('--initialize-at-build-time=com.example.EagerClass')
```

Inspect build diagnostics:

```groovy
buildArgs.add('--diagnostics-mode')
```

Include resource files at runtime:

```groovy
buildArgs.add('-H:IncludeResources=.*\\.(properties|xml)$')
```

Pass arguments to the application at startup:

```groovy
runtimeArgs.add('--server.port=8080')
```

### Gradle Full Example

Groovy DSL:

```groovy
graalvmNative {
    binaries {
        main {
            imageName = 'myapp'
            mainClass = 'com.example.Main'
            verbose = true
            buildArgs.addAll(
                '--initialize-at-run-time=com.example.Lazy',
                '-H:IncludeResources=.*\\.properties$',
                '-O3'
            )
            jvmArgs.add('-Xmx8g')
        }
        test {
            imageName = 'myapp-tests'
        }
        all {
            javaLauncher = javaToolchains.launcherFor {
                languageVersion.set(JavaLanguageVersion.of(21))
            }
        }
    }
}
```

Kotlin DSL:

```kotlin
graalvmNative {
    binaries {
        named("main") {
            imageName.set("myapp")
            mainClass.set("com.example.Main")
            verbose.set(true)
            buildArgs.addAll(
                "--initialize-at-run-time=com.example.Lazy",
                "-H:IncludeResources=.*\\.properties$",
                "-O3"
            )
            jvmArgs.add("-Xmx8g")
        }
        named("test") {
            imageName.set("myapp-tests")
        }
    }
}
```

## Missing Reachability Metadata

When Native Image reports missing reflection, resources, serialization, proxy, or JNI entries, use [reachability-metadata.md](reachability-metadata.md).

To enable exact metadata checking and warning mode in Maven, add to plugin configuration:

```xml
<configuration>
  <buildArgs>
    <buildArg>--exact-reachability-metadata</buildArg>
  </buildArgs>
  <runtimeArgs>
    <runtimeArg>-XX:MissingRegistrationReportingMode=Warn</runtimeArg>
  </runtimeArgs>
</configuration>
```

To enable exact metadata checking and warning mode in Gradle, add to `binaries.all`:

```groovy
graalvmNative {
  binaries.all {
    buildArgs.add('--exact-reachability-metadata')
    runtimeArgs.add('-XX:MissingRegistrationReportingMode=Warn')
  }
}
```

To collect metadata with the Gradle tracing agent:

```bash
./gradlew generateMetadata -Pcoordinates=<library-coordinates> -PagentAllowedPackages=<condition-packages>
```

## Native Testing

For Maven native tests:

```bash
./mvnw -Pnative test
```

For Gradle native tests:

```bash
./gradlew nativeTest
```

The Gradle native test binary is located at:

```text
build/native/nativeTestCompile/<imageName>
```

## Sources

- https://github.com/oracle/graal/tree/master/substratevm/skills/build-native-image-maven
- https://github.com/oracle/graal/tree/master/substratevm/skills/build-native-image-gradle
- https://graalvm.github.io/native-build-tools/latest/index.html
