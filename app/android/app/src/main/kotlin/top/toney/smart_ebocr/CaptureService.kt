package top.toney.smart_ebocr

import android.provider.Settings
import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Activity
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Environment
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.DisplayMetrics
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.graphics.drawable.GradientDrawable
import android.widget.ImageView
import android.os.VibrationEffect
import android.os.Vibrator
import android.util.Log
import android.os.VibratorManager
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer

class CaptureService : Service() {

    companion object {
        const val ACTION_START = "top.toney.smart_ebocr.CAPTURE_START"
        const val ACTION_STOP = "top.toney.smart_ebocr.CAPTURE_STOP"
        const val CHANNEL_ID = "smart_ebocr_capture_channel"

        var permissionResult: Intent? = null
        var instance: CaptureService? = null
        var isOverlayReady = false
    }

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var windowManager: WindowManager? = null
    private var floatingView: View? = null
    private var screenWidth = 0
    private var screenHeight = 0
    private var screenDensity = 0
    private val handler = Handler(Looper.getMainLooper())
    var screenshotListener: ((String) -> Unit)? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val metrics = DisplayMetrics()
        windowManager?.defaultDisplay?.getMetrics(metrics)
        screenWidth = metrics.widthPixels
        screenHeight = metrics.heightPixels
        screenDensity = metrics.densityDpi
        Log.i("SmartEBOCR", "CaptureService.onCreate: screen=${screenWidth}x${screenHeight}, density=$screenDensity")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.i("SmartEBOCR", "CaptureService.onStartCommand: action=${intent?.action}, permissionResult=${permissionResult != null}")
        when (intent?.action) {
            ACTION_START -> {
                startForegroundNotification()
                setupMediaProjection()
                showFloatingButton()
                Log.i("SmartEBOCR", "CaptureService onStartCommand done: mediaProjection=${mediaProjection != null}, imageReader=${imageReader != null}, overlayReady=$isOverlayReady")
            }
            ACTION_STOP -> {
                cleanup()
                stopSelf()
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        cleanup()
        instance = null
        super.onDestroy()
    }

    private fun startForegroundNotification() {
        try {
            val channel = NotificationChannel(
                CHANNEL_ID,
                getString(R.string.capture_notification_channel),
                NotificationManager.IMPORTANCE_LOW
            )
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(channel)

            val notification = Notification.Builder(this, CHANNEL_ID)
                .setContentTitle(getString(R.string.capture_notification_title))
                .setContentText(getString(R.string.capture_notification_text))
                .setSmallIcon(android.R.drawable.ic_menu_camera)
                .setOngoing(true)
                .build()

            startForeground(1, notification)
        } catch (e: Exception) {
            Log.e("CaptureService", "startForeground failed", e)
        }
    }

    private fun setupMediaProjection() {
        val data = permissionResult
        if (data == null) {
            Log.e("SmartEBOCR", "setupMediaProjection: permissionResult is NULL — user must grant screen capture first")
            return
        }
        val manager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        mediaProjection = manager.getMediaProjection(Activity.RESULT_OK, data)
        Log.i("SmartEBOCR", "MediaProjection created: ${mediaProjection != null}")

        if (mediaProjection == null) {
            Log.e("SmartEBOCR", "getMediaProjection returned null")
            return
        }

        // Android 14+ 要求在 createVirtualDisplay 之前注册回调
        mediaProjection?.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() {
                Log.w("SmartEBOCR", "MediaProjection stopped by system")
                cleanup()
                stopSelf()
            }
        }, handler)

        imageReader = ImageReader.newInstance(screenWidth, screenHeight, PixelFormat.RGBA_8888, 2)
        Log.i("SmartEBOCR", "ImageReader created: ${imageReader != null}, size=${screenWidth}x${screenHeight}")

        virtualDisplay = mediaProjection?.createVirtualDisplay(
            "SmartEBOCR Capture",
            screenWidth, screenHeight, screenDensity,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader?.surface, null, handler
        )
        Log.i("SmartEBOCR", "VirtualDisplay created: ${virtualDisplay != null}")
    }

    @SuppressLint("ClickableViewAccessibility", "InflateParams")
    private fun showFloatingButton() {
        if (!Settings.canDrawOverlays(this)) {
            isOverlayReady = false
            return
        }
        if (floatingView != null) return

        floatingView = ImageView(this).apply {
            setImageResource(android.R.drawable.ic_menu_camera)
            val density = resources.displayMetrics.density
            background = GradientDrawable().apply {
                setColor(0x802196F3.toInt())
                cornerRadius = 16f * density
            }
            val pad = (12 * density).toInt()
            setPadding(pad, pad, pad, pad)
            setOnTouchListener(FloatingTouchListener(context, this@CaptureService))
        }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_SYSTEM_ALERT,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = screenWidth - 200
            y = screenHeight / 2
        }

        try {
            windowManager?.addView(floatingView, params)
            isOverlayReady = true
        } catch (e: Exception) {
            Log.w("CaptureService", "悬浮窗添加失败: ${e.message}")
            floatingView = null
            isOverlayReady = false
        }
    }

    private fun hideFloatingButton() {
        floatingView?.let {
            windowManager?.removeView(it)
            floatingView = null
        }
    }

    private fun getScreenshotDir(): File? {
        val dir = File(getExternalFilesDir(null), "screenshots")
        if (!dir.exists()) dir.mkdirs()
        return dir
    }

    fun captureScreenshotWithoutOverlay(filename: String, callback: ((String?) -> Unit)? = null) {
        floatingView?.visibility = View.INVISIBLE
        handler.postDelayed({
            captureScreenshot(filename) { path ->
                floatingView?.visibility = View.VISIBLE
                callback?.invoke(path)
            }
        }, 200)
    }

    fun captureScreenshot(filename: String, callback: ((String?) -> Unit)? = null) {
        val image: Image? = imageReader?.acquireLatestImage()
        if (image == null) {
            Log.w("CaptureService", "acquireLatestImage returned null, imageReader=$imageReader")
            handler.post { callback?.invoke(null) }
            return
        }

        Thread {
            try {
                val planes = image.planes
                val buffer: ByteBuffer = planes[0].buffer
                val pixelStride = planes[0].pixelStride
                val rowStride = planes[0].rowStride
                val rowPadding = rowStride - pixelStride * screenWidth

                val bmpWidth = screenWidth + rowPadding / pixelStride
                val bitmap = Bitmap.createBitmap(bmpWidth, screenHeight, Bitmap.Config.ARGB_8888)
                bitmap.copyPixelsFromBuffer(buffer)

                val cropped = Bitmap.createBitmap(bitmap, 0, 0, screenWidth, screenHeight)

                val dir = getScreenshotDir()
                if (dir == null) {
                    handler.post { callback?.invoke(null) }
                    return@Thread
                }
                val file = File(dir, filename)

                FileOutputStream(file).use { fos ->
                    cropped.compress(Bitmap.CompressFormat.JPEG, 95, fos)
                }

                bitmap.recycle()
                cropped.recycle()

                handler.post { callback?.invoke(file.absolutePath) }
            } catch (e: Exception) {
                Log.e("CaptureService", "captureScreenshot failed", e)
                handler.post { callback?.invoke(null) }
            } finally {
                image.close()
            }
        }.start()
    }

    private fun cleanup() {
        hideFloatingButton()
        virtualDisplay?.release()
        virtualDisplay = null
        imageReader?.close()
        imageReader = null
        mediaProjection?.stop()
        mediaProjection = null
    }

    class FloatingTouchListener(
        private val context: Context,
        private val service: CaptureService
    ) : View.OnTouchListener {
        private var initialX = 0
        private var initialY = 0
        private var initialTouchX = 0f
        private var initialTouchY = 0f
        private var isMoved = false
        private val handler = Handler(Looper.getMainLooper())

        @SuppressLint("ClickableViewAccessibility")
        override fun onTouch(v: View, event: MotionEvent): Boolean {
            val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
            val params = v.layoutParams as WindowManager.LayoutParams

            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = params.x
                    initialY = params.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    isMoved = false
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = (event.rawX - initialTouchX).toInt()
                    val dy = (event.rawY - initialTouchY).toInt()
                    if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
                        params.x = initialX + dx
                        params.y = initialY + dy
                        wm.updateViewLayout(v, params)
                        isMoved = true
                    }
                }
                MotionEvent.ACTION_UP -> {
                    if (!isMoved) {
                        val filename = "temp_${System.currentTimeMillis()}.jpg"
                        service.captureScreenshotWithoutOverlay(filename) { path ->
                            flashButton(v, path != null)
                            vibrate(path != null)
                            if (path != null) {
                                service.screenshotListener?.invoke(path)
                            }
                        }
                    }
                }
            }
            return true
        }

        private fun flashButton(v: View, success: Boolean) {
            val color = if (success) 0x8000C853.toInt() else 0x80FF1744.toInt()
            (v.background as? GradientDrawable)?.setColor(color)
            handler.postDelayed({
                (v.background as? GradientDrawable)?.setColor(0x802196F3.toInt())
            }, 400)
        }

        @Suppress("DEPRECATION")
        private fun vibrate(success: Boolean) {
            val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager)
                    .defaultVibrator
            } else {
                context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            }
            if (success) {
                vibrator.vibrate(VibrationEffect.createOneShot(80, 128))
            } else {
                vibrator.vibrate(VibrationEffect.createWaveform(
                    longArrayOf(0, 100, 80, 100), intArrayOf(0, 200, 0, 200), -1
                ))
            }
        }
    }
}
