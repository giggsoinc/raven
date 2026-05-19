---
name: oracle-graal-specialist
description: GraalVM Native Image — builds, configuration, reachability metadata, and troubleshooting. Trigger on: native-image, GraalVM, native-maven-plugin, org.graalvm.buildtools.native, reachability metadata, reflection config, JNI config, Native Build Tools.
---

# GraalVM Native Image Specialist

## Fetch Protocol

All reference guides live at `https://raw.githubusercontent.com/giggsoinc/skills/main/graal/`.
Use WebFetch to pull the specific file when a topic matches the routing table.
On network failure: answer from built-in GraalVM knowledge and note the limitation.

## Category Routing

| Topic | Fetch URL |
|-------|-----------|
| `native-image` CLI, options, classpath, modules, output names, optimization, URL protocols | `https://raw.githubusercontent.com/giggsoinc/skills/main/graal/native-image/build-native-image.md` |
| Maven `native-maven-plugin`, Gradle `org.graalvm.buildtools.native`, build tasks, plugin options | `https://raw.githubusercontent.com/giggsoinc/skills/main/graal/native-image/native-build-tools.md` |
| Missing reflection, JNI, resources, serialization, dynamic proxies, conditional metadata | `https://raw.githubusercontent.com/giggsoinc/skills/main/graal/native-image/reachability-metadata.md` |
| Build failures, runtime failures, missing metadata symptoms, class init issues, diagnostics | `https://raw.githubusercontent.com/giggsoinc/skills/main/graal/native-image/troubleshooting.md` |

## Common Flows

| Task | Fetch sequence |
|------|----------------|
| Build a Java class with Native Image | `native-image/build-native-image.md` |
| Configure Maven/Gradle for Native Image | `native-image/native-build-tools.md` → `native-image/build-native-image.md` for flags |
| Fix missing reflection/JNI/proxy/resource metadata | `native-image/reachability-metadata.md` |
| Diagnose build or runtime failures | `native-image/troubleshooting.md` → `native-image/build-native-image.md` → `native-image/reachability-metadata.md` |

Full source: https://github.com/giggsoinc/skills/tree/main/graal
