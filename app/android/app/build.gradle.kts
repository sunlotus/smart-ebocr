plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "top.toney.smart_ebocr"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        applicationId = "top.toney.smart_ebocr"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        ndk {
            abiFilters.addAll(listOf("arm64-v8a", "armeabi-v7a"))
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("debug")
            ndk {
                abiFilters.addAll(listOf("arm64-v8a", "armeabi-v7a"))
            }
        }
    }
}

flutter {
    source = "../.."
}

// 任务：复制 APK 为 smart-ebocr-app-release.apk
tasks.register("copyApk") {
    doLast {
        val flutterApkDir = file("${project.layout.buildDirectory.get()}/outputs/flutter-apk")
        val source = file("${flutterApkDir}/app-release.apk")
        val target = file("${flutterApkDir}/smart-ebocr-app-release.apk")
        if (source.exists()) {
            source.copyTo(target, overwrite = true)
            println("APK copied as: ${target.name}")
        }
    }
}

// 在所有任务创建完成后配置
afterEvaluate {
    tasks.named("assembleRelease") {
        finalizedBy("copyApk")
    }
}
