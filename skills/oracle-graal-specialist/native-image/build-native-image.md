# Building Native Image

## Overview

Use this skill to build Java applications with GraalVM Native Image and configure raw `native-image` command-line options.

## Prerequisites

- Set `JAVA_HOME` to a GraalVM distribution if your Java program uses the Native Image SDK. If you do not know the path, ask the user to provide it.

## Build and Run

Use [native-build-tools.md](native-build-tools.md) whenever possible for Maven or Gradle projects. Use the raw `native-image` command directly for simple Java files or cases where the user specifically asks for direct CLI usage.

1. Compile your Java file with `javac`.
2. Build the Native Image:

   ```bash
   $JAVA_HOME/bin/native-image <app-name>
   ```

3. Run the resulting executable:

   ```bash
   ./app-name
   ```

4. For classpath-based builds, pass the classpath explicitly with the `-cp` option.

## Classpath and Modules

For classpath-based applications:

```bash
native-image -cp <path1>:<path2> <class>
```

If using modules:

```bash
native-image -p <module-path> --add-modules <module-name> <class>
```

## Build-Time Inputs

If you need to set a system property at build time:

```bash
native-image -Dkey=value <class>
```

If you need to pass a flag to the JVM running the builder:

```bash
native-image -J<flag> <class>
```

For class initialization, linking, builder memory, or missing metadata failures, use [troubleshooting.md](troubleshooting.md). For metadata file structure and JSON entries, see [reachability-metadata.md](reachability-metadata.md).

## Output and Binary Type

If you want to rename the output binary:

```bash
native-image -o myapp <class>
```

If you want to build a shared library:

```bash
native-image --shared <class>
```

If you want a fully statically linked binary:

```bash
native-image --static --libc=musl <class>
```

If you want static linking but keep libc dynamic:

```bash
native-image --static-nolibc <class>
```

## Performance and Optimization

If you want fastest build time during development iteration:

```bash
native-image -Ob <class>
```

If you want best runtime performance:

```bash
native-image -O3 <class>
```

If you want to optimize for binary size:

```bash
native-image -Os <class>
```

If you want to change the garbage collector:

```bash
native-image --gc=epsilon <class>  # no GC (throughput)
native-image --gc=serial <class>   # default
```

If you want to target the current machine's CPU features:

```bash
native-image -march=native <class>
```

If you need maximum compatibility across machines:

```bash
native-image -march=compatibility <class>
```

If you want to limit build parallelism:

```bash
native-image --parallelism=4 <class>
```

## Network Support

If the binary needs HTTP/HTTPS:

```bash
native-image --enable-http --enable-https <class>
```

If the binary needs specific URL protocols:

```bash
native-image --enable-url-protocols=http,https <class>
```

## Monitoring and Observability

If you need runtime monitoring such as heap dumps, JFR, or thread dumps:

```bash
native-image --enable-monitoring=heapdump,jfr,threaddump <class>
```

## Security and Compliance

If you need all security services, such as TLS/SSL:

```bash
native-image --enable-all-security-services <class>
```

## Cross-Compilation and Platform

If you need to cross-compile for a different OS or architecture:

```bash
native-image --target=linux-aarch64 <class>
```

If you need a custom C compiler:

```bash
native-image --native-compiler-path=/usr/bin/gcc <class>
```

## Info and Discovery

If you want to list available CPU features:

```bash
native-image --list-cpu-features
```

If you want to list observable modules:

```bash
native-image --list-modules
```

If you want to see the native toolchain and build settings:

```bash
native-image --native-image-info
```

## Troubleshooting

If you encounter runtime errors related to reflection, JNI, resources, serialization, or dynamic proxies, see [reachability-metadata.md](reachability-metadata.md) before attempting a fix. For problem-based routing, see [troubleshooting.md](troubleshooting.md).

## Sources

- https://github.com/oracle/graal/tree/master/substratevm/skills/building-native-image
- https://www.graalvm.org/latest/reference-manual/native-image/
- https://www.graalvm.org/latest/reference-manual/native-image/overview/Options/
