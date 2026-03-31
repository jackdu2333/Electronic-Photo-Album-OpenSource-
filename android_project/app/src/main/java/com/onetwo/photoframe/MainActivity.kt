package com.onetwo.photoframe

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.KeyEvent
import android.view.View
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import android.webkit.CookieManager
import android.webkit.SslErrorHandler
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible

class MainActivity : AppCompatActivity() {

    companion object {
        private const val PREFS_NAME = "photo_frame_prefs"
        private const val KEY_SERVER_URL = "server_url"
    }

    private lateinit var webView: WebView
    private lateinit var prefs: SharedPreferences
    private lateinit var serverSetupContainer: ScrollView
    private lateinit var serverUrlInput: EditText
    private lateinit var saveServerButton: Button
    private lateinit var changeServerButton: Button
    private lateinit var serverStatusText: TextView

    // --- File Upload Support ---
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private val FILE_CHOOSER_REQUEST_CODE = 101
    private var currentServerUrl: String? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 1. Keep Screen On
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        // 2. Inflate screen
        setContentView(R.layout.activity_main)

        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        webView = findViewById(R.id.web_view)
        serverSetupContainer = findViewById(R.id.server_setup_container)
        serverUrlInput = findViewById(R.id.server_url_input)
        saveServerButton = findViewById(R.id.save_server_button)
        changeServerButton = findViewById(R.id.change_server_button)
        serverStatusText = findViewById(R.id.server_status_text)

        // 3. Immersive Mode (Hide System Bars)
        hideSystemUI()

        // 4. Configure WebView
        configureWebView()
        configureSetupUi()

        val savedServerUrl = prefs.getString(KEY_SERVER_URL, null)?.trim().takeUnless { it.isNullOrEmpty() }
        if (savedServerUrl != null) {
            connectToServer(savedServerUrl)
        } else {
            showServerSetup()
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun configureWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true // Essential for localStorage
            useWideViewPort = true
            loadWithOverviewMode = true
            cacheMode = WebSettings.LOAD_DEFAULT
            mediaPlaybackRequiresUserGesture = false // Allow auto-play video/audio
            allowContentAccess = true
            allowFileAccess = true
        }

        val cookieManager = CookieManager.getInstance()
        cookieManager.setAcceptCookie(true)
        cookieManager.setAcceptThirdPartyCookies(webView, true)

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                return false
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                currentServerUrl = url ?: currentServerUrl
                hideServerSetup()
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                super.onReceivedError(view, request, error)
                if (request?.isForMainFrame == true) {
                    val message = error?.description?.toString()?.trim()
                    showServerSetup(
                        prefillUrl = currentServerUrl,
                        message = if (message.isNullOrEmpty()) {
                            getString(R.string.server_error_load_failed)
                        } else {
                            getString(R.string.server_error_load_failed) + "\n" + message
                        }
                    )
                }
            }

            override fun onReceivedSslError(
                view: WebView?,
                handler: SslErrorHandler?,
                error: android.net.http.SslError?
            ) {
                handler?.cancel()
                showServerSetup(
                    prefillUrl = currentServerUrl,
                    message = getString(R.string.server_error_ssl)
                )
            }
        }

        // --- WebChromeClient: Required for file chooser on Android ---
        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                // Cancel any previous callback
                this@MainActivity.filePathCallback?.onReceiveValue(null)
                this@MainActivity.filePathCallback = filePathCallback

                val intent = fileChooserParams?.createIntent() ?: Intent(Intent.ACTION_GET_CONTENT).apply {
                    type = "image/*"
                    putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
                }
                try {
                    startActivityForResult(intent, FILE_CHOOSER_REQUEST_CODE)
                } catch (e: Exception) {
                    this@MainActivity.filePathCallback = null
                    return false
                }
                return true
            }
        }
    }

    private fun configureSetupUi() {
        saveServerButton.setOnClickListener {
            val normalized = normalizeServerUrl(serverUrlInput.text?.toString())
            if (normalized == null) {
                showStatus(getString(R.string.server_error_invalid))
                return@setOnClickListener
            }

            prefs.edit().putString(KEY_SERVER_URL, normalized).apply()
            connectToServer(normalized)
        }

        changeServerButton.setOnClickListener {
            showServerSetup(
                prefillUrl = currentServerUrl,
                message = getString(R.string.server_change_hint)
            )
        }
    }

    private fun connectToServer(url: String) {
        currentServerUrl = url
        saveServerButton.isEnabled = false
        saveServerButton.text = getString(R.string.server_status_connecting)
        showStatus(getString(R.string.server_status_connecting), isError = false)
        webView.loadUrl(url)
    }

    private fun showServerSetup(prefillUrl: String? = null, message: String? = null) {
        serverSetupContainer.visibility = View.VISIBLE
        changeServerButton.visibility = View.GONE
        saveServerButton.isEnabled = true
        saveServerButton.text = getString(R.string.server_setup_save)

        val candidate = prefillUrl
            ?: currentServerUrl
            ?: prefs.getString(KEY_SERVER_URL, null)
            ?: ""
        serverUrlInput.setText(candidate)
        serverUrlInput.setSelection(serverUrlInput.text.length)
        if (message.isNullOrBlank()) {
            serverStatusText.visibility = View.GONE
        } else {
            showStatus(message)
        }
    }

    private fun hideServerSetup() {
        serverSetupContainer.visibility = View.GONE
        changeServerButton.visibility = View.VISIBLE
        serverStatusText.visibility = View.GONE
        webView.visibility = View.VISIBLE

        // Keep remote/touch interaction on the page natural after successful connect.
        webView.isFocusable = true
        webView.isFocusableInTouchMode = true
        webView.requestFocus()
    }

    private fun showStatus(message: String, isError: Boolean = true) {
        serverStatusText.visibility = View.VISIBLE
        serverStatusText.text = message
        serverStatusText.setTextColor(
            if (isError) 0xFFFFB4B4.toInt() else 0xFFB6C3D6.toInt()
        )
    }

    private fun normalizeServerUrl(raw: String?): String? {
        val value = raw?.trim().orEmpty()
        if (value.isEmpty()) return null

        val uri = Uri.parse(value)
        val scheme = uri.scheme?.lowercase()
        if (scheme != "http" && scheme != "https") return null
        if (uri.host.isNullOrBlank()) return null

        return value.trimEnd('/')
    }

    // Handle result from file picker
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == FILE_CHOOSER_REQUEST_CODE) {
            val results: Array<Uri>? = if (resultCode == Activity.RESULT_OK) {
                when {
                    data?.clipData != null -> {
                        // Multiple files selected
                        val count = data.clipData!!.itemCount
                        Array(count) { i -> data.clipData!!.getItemAt(i).uri }
                    }
                    data?.data != null -> arrayOf(data.data!!)
                    else -> null
                }
            } else null

            filePathCallback?.onReceiveValue(results)
            filePathCallback = null
        } else {
            super.onActivityResult(requestCode, resultCode, data)
        }
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) {
            hideSystemUI()
        }
    }

    override fun onResume() {
        super.onResume()
        hideSystemUI()
    }

    override fun onPause() {
        super.onPause()
        CookieManager.getInstance().flush()
    }

    override fun onDestroy() {
        CookieManager.getInstance().flush()
        webView.destroy()
        super.onDestroy()
    }

    private fun hideSystemUI() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.insetsController?.let { controller ->
                controller.hide(WindowInsets.Type.statusBars() or WindowInsets.Type.navigationBars())
                controller.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility = (
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                            or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                            or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                            or View.SYSTEM_UI_FLAG_FULLSCREEN
                    )
        }
    }

    override fun dispatchKeyEvent(event: KeyEvent?): Boolean {
        if (event?.action == KeyEvent.ACTION_DOWN) {
            Log.d("PhotoFrame", "Key Down: ${event.keyCode}")
            when (event.keyCode) {
                KeyEvent.KEYCODE_MENU -> {
                    showServerSetup(
                        prefillUrl = currentServerUrl,
                        message = getString(R.string.server_change_hint)
                    )
                    return true
                }
                KeyEvent.KEYCODE_BACK -> {
                    if (serverSetupContainer.isVisible && !currentServerUrl.isNullOrBlank()) {
                        hideServerSetup()
                        return true
                    }
                }
                KeyEvent.KEYCODE_DPAD_LEFT -> {
                    if (!serverSetupContainer.isVisible) {
                        Log.d("PhotoFrame", "DPAD LEFT detected, executing prevImage()")
                        webView.post { webView.loadUrl("javascript:prevImage()") }
                        return true
                    }
                }
                KeyEvent.KEYCODE_DPAD_RIGHT, KeyEvent.KEYCODE_DPAD_CENTER, KeyEvent.KEYCODE_ENTER -> {
                    if (!serverSetupContainer.isVisible) {
                        Log.d("PhotoFrame", "DPAD RIGHT/ENTER detected, executing nextImage()")
                        webView.post { webView.loadUrl("javascript:nextImage()") }
                        return true
                    }
                }
            }
        }
        return super.dispatchKeyEvent(event)
    }
}
