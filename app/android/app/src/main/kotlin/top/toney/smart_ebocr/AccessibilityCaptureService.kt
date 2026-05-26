package top.toney.smart_ebocr

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.util.Calendar

class AccessibilityCaptureService : AccessibilityService() {

    companion object {
        const val ACTION_START_AUTO = "top.toney.smart_ebocr.START_AUTO"
        const val ACTION_STOP_AUTO = "top.toney.smart_ebocr.STOP_AUTO"

        var instance: AccessibilityCaptureService? = null
        var isRunning = false
    }

    private var targetYear = 0
    private var targetMonth = 0
    private var currentDayIndex = 0
    private var daysInMonth = 0
    private var completedCount = 0
    private var skippedCount = 0

    private val SGCC_PACKAGE = "com.sgcc.evs.electriccharge"

    override fun onServiceConnected() {
        instance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (!isRunning || event == null) return
        if (event.packageName?.toString() != SGCC_PACKAGE) return

        val rootNode = rootInActiveWindow ?: return
        val hasElectricityData = checkElectricityData(rootNode)

        val dayStr = String.format("%04d%02d%02d", targetYear, targetMonth, currentDayIndex + 1)

        if (hasElectricityData) {
            val captureService = CaptureService.instance
            if (captureService != null) {
                captureService.captureScreenshot("$dayStr.jpg")
                completedCount++
            }
        } else {
            skippedCount++
        }

        currentDayIndex++

        if (currentDayIndex >= daysInMonth) {
            isRunning = false
            return
        }
    }

    override fun onInterrupt() {
        isRunning = false
    }

    override fun onDestroy() {
        instance = null
        isRunning = false
        super.onDestroy()
    }

    fun startAutoCapture(year: Int, month: Int) {
        targetYear = year
        targetMonth = month
        val cal = Calendar.getInstance()
        cal.set(year, month - 1, 1)
        daysInMonth = cal.getActualMaximum(Calendar.DAY_OF_MONTH)
        currentDayIndex = 0
        completedCount = 0
        skippedCount = 0
        isRunning = true
    }

    fun stopAutoCapture() {
        isRunning = false
    }

    private fun checkElectricityData(node: AccessibilityNodeInfo): Boolean {
        val text = node.text?.toString() ?: ""
        if (text.contains("千瓦时") || text.contains("kWh")) {
            return true
        }

        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            if (checkElectricityData(child)) {
                child.recycle()
                return true
            }
            child.recycle()
        }
        return false
    }
}
