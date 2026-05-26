package top.toney.smart_ebocr

import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.util.Log
import io.flutter.embedding.android.FlutterActivity
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val CHANNEL = "com.smart_ebocr.capture/methods"
    private val REQUEST_MEDIA_PROJECTION = 1001

    private var pendingResult: MethodChannel.Result? = null
    private var captureService: CaptureService? = null
    private var methodChannel: MethodChannel? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        methodChannel = MethodChannel(flutterEngine!!.dartExecutor.binaryMessenger, CHANNEL)
        methodChannel?.setMethodCallHandler { call, result ->
            when (call.method) {
                "requestPermission" -> requestMediaProjectionPermission(result)
                "canDrawOverlays" -> result.success(Settings.canDrawOverlays(this))
                "requestOverlayPermission" -> {
                    val intent = Intent(
                        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:$packageName")
                    )
                    startActivity(intent)
                    result.success(null)
                }
                "startCapture" -> startCapture(result)
                "stopCapture" -> stopCapture(result)
                "captureScreenshot" -> {
                    val filename = call.argument<String>("filename") ?: "unknown.jpg"
                    captureScreenshot(filename, result)
                }
                "startAutoCapture" -> {
                    val year = call.argument<Int>("year") ?: 0
                    val month = call.argument<Int>("month") ?: 0
                    startAutoCapture(year, month, result)
                }
                "stopAutoCapture" -> stopAutoCapture(result)
                else -> result.notImplemented()
            }
        }
    }

    private fun requestMediaProjectionPermission(result: MethodChannel.Result) {
        Log.i("SmartEBOCR", "requestMediaProjectionPermission: showing system dialog")
        pendingResult = result
        val manager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        startActivityForResult(manager.createScreenCaptureIntent(), REQUEST_MEDIA_PROJECTION)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == REQUEST_MEDIA_PROJECTION) {
            Log.i("SmartEBOCR", "onActivityResult: requestCode=$requestCode, resultCode=$resultCode, data=${data != null}")
            if (resultCode == RESULT_OK && data != null) {
                CaptureService.permissionResult = data
                Log.i("SmartEBOCR", "MediaProjection permission granted, permissionResult saved")
                pendingResult?.success(true)
            } else {
                Log.w("SmartEBOCR", "MediaProjection permission denied")
                pendingResult?.success(false)
            }
            pendingResult = null
            return
        }
        super.onActivityResult(requestCode, resultCode, data)
    }

    private fun startCapture(result: MethodChannel.Result) {
        Log.i("SmartEBOCR", "startCapture: permissionResult=${CaptureService.permissionResult != null}, instance=${CaptureService.instance != null}")
        val intent = Intent(this, CaptureService::class.java).apply {
            action = CaptureService.ACTION_START
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
        // 延迟检查悬浮窗是否创建成功
        Handler(Looper.getMainLooper()).postDelayed({
            // 注册悬浮按钮截图监听
            CaptureService.instance?.screenshotListener = { path ->
                methodChannel?.invokeMethod("onScreenshotCaptured", mapOf("path" to path))
            }
            result.success(CaptureService.isOverlayReady)
        }, 500)
    }

    private fun stopCapture(result: MethodChannel.Result) {
        val intent = Intent(this, CaptureService::class.java).apply {
            action = CaptureService.ACTION_STOP
        }
        startService(intent)
        result.success(null)
    }

    private fun captureScreenshot(filename: String, result: MethodChannel.Result) {
        val service = CaptureService.instance
        if (service == null) {
            result.error("NOT_RUNNING", "CaptureService is not running", null)
            return
        }
        service.captureScreenshot(filename) { path ->
            if (path != null) {
                result.success(path)
                // 通知 Flutter 截图成功
                methodChannel?.invokeMethod("onScreenshotCaptured", mapOf("path" to path))
            } else {
                result.error("CAPTURE_FAILED", "Failed to capture screenshot", null)
            }
        }
    }

    private fun startAutoCapture(year: Int, month: Int, result: MethodChannel.Result) {
        val service = AccessibilityCaptureService.instance
        if (service == null) {
            result.error("NOT_ENABLED", "Accessibility service is not enabled", null)
            return
        }
        service.startAutoCapture(year, month)
        result.success(null)
    }

    private fun stopAutoCapture(result: MethodChannel.Result) {
        AccessibilityCaptureService.instance?.stopAutoCapture()
        result.success(null)
    }
}
