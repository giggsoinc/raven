---
name: graal
description: Build, configure, and troubleshoot GraalVM Native Image applications. Use this skill for native-image CLI builds, Maven or Gradle Native Build Tools, reachability metadata, and build or run time issue diagnosis.
---

# Oracle Graal Skills

Use this domain to build, configure, and troubleshoot GraalVM Native Image applications with Maven, Gradle, or the CLI.

## How to Use This Domain

1. Start with the routing table below.
2. Read only the specific Native Image file needed for the task.
3. Prefer Native Build Tools for Maven or Gradle projects. Use the raw `native-image` workflow for simple Java files or direct CLI usage.

## Directory Structure

```text
graal/
|-- SKILL.md
`-- native-image/
    |-- build-native-image.md
    |-- native-build-tools.md
    |-- reachability-metadata.md
    `-- troubleshooting.md
```

## Category Routing

| Topic | File |
|-------|------|
| `native-image` CLI builds, options, classpath, modules, output names, binary type, optimization, URL protocols, monitoring, security | `graal/native-image/build-native-image.md` |
| Maven `native-maven-plugin`, Gradle `org.graalvm.buildtools.native`, build-tool tasks, plugin options, and native test routing | `graal/native-image/native-build-tools.md` |
| Missing reflection, JNI, resources, resource bundles, serialization, dynamic proxies, conditional metadata, and `reachability-metadata.json` layout | `graal/native-image/reachability-metadata.md` |
| Build failures, runtime failures, missing metadata symptoms, class initialization issues, memory issues, diagnostics, Maven activation issues, and where to route fixes | `graal/native-image/troubleshooting.md` |

## Key Starting Points

- `graal/native-image/build-native-image.md`
- `graal/native-image/native-build-tools.md`
- `graal/native-image/reachability-metadata.md`
- `graal/native-image/troubleshooting.md`

## Common Multi-Step Flows

| Task | Recommended Sequence |
|------|----------------------|
| Build a Java class with Native Image | `native-image/build-native-image.md` |
| Configure a Maven or Gradle project for Native Image | `native-image/native-build-tools.md` -> `native-image/build-native-image.md` for flags |
| Fix missing reflection, JNI, proxy, resource, bundle, or serialization metadata | `native-image/reachability-metadata.md` |
| Diagnose build failures or runtime behavior differences | `native-image/troubleshooting.md` -> `native-image/build-native-image.md` -> `native-image/reachability-metadata.md` if metadata is involved |

## Sources

- https://github.com/oracle/graal/tree/master/substratevm/skills/building-native-image
- https://github.com/oracle/graal/tree/master/substratevm/skills/build-native-image-maven
- https://github.com/oracle/graal/tree/master/substratevm/skills/build-native-image-gradle
- https://www.graalvm.org/latest/reference-manual/native-image/
