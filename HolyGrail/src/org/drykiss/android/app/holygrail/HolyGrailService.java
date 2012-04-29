package org.drykiss.android.app.holygrail;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.lang.reflect.Method;
import java.net.ServerSocket;
import java.net.Socket;

import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.PixelFormat;
import android.os.Handler;
import android.os.IBinder;
import android.util.Log;
import android.view.Display;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.ImageView;

public class HolyGrailService extends Service {
    private static final String TAG = "HolyGrailService";

    private static final int CURSOR_DISPLAY_TIMEOUT = 5000;
    Class mWindowManagerImplClass;
    Object mWM;
    Method mGetDefaultWM;
    Method mAddView;
    Method mUpdateLayout;
    ImageView mCursorView;
    WindowManager.LayoutParams mParams;
    Display mCurrentDisplay;
    final Handler mHandler = new Handler();

    @Override
    public IBinder onBind(Intent intent) {
        // TODO Auto-generated method stub
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        
        init();
        startServer();
    }

    private void init() {
        try {
            mWindowManagerImplClass = Class
                    .forName("android.view.WindowManagerImpl");
            mGetDefaultWM = mWindowManagerImplClass
                    .getDeclaredMethod("getDefault");
            mGetDefaultWM.setAccessible(true);
            mWM = mGetDefaultWM.invoke(mWindowManagerImplClass);

            mAddView = mWindowManagerImplClass.getDeclaredMethod("addView",
                    View.class, ViewGroup.LayoutParams.class);
            mAddView.setAccessible(true);

            mUpdateLayout = mWindowManagerImplClass.getDeclaredMethod(
                    "updateViewLayout", View.class,
                    ViewGroup.LayoutParams.class);
            mUpdateLayout.setAccessible(true);

            ImageView cursorView = new ImageView(this);
            cursorView.setImageResource(R.drawable.cursor_pressed);
            mCursorView = cursorView;

            final WindowManager.LayoutParams params = new WindowManager.LayoutParams();
            params.height = WindowManager.LayoutParams.WRAP_CONTENT;
            params.width = WindowManager.LayoutParams.WRAP_CONTENT;
            params.flags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                    | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                    | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON;
            params.format = PixelFormat.TRANSLUCENT;
            // params.windowAnimations =
            // com.android.internal.R.style.Animation_Toast;
            params.type = WindowManager.LayoutParams.TYPE_TOAST;
            params.setTitle("Holy grail cursor");
            mParams = params;

            mAddView.invoke(mWM, mCursorView, mParams);
            hideCursor();

            mCurrentDisplay = ((WindowManager) getSystemService(Context.WINDOW_SERVICE))
                    .getDefaultDisplay();

        } catch (Throwable e) {
            Log.e(TAG, "Fail to get hidden grail!!", e);
        }
    }

    private void hideCursor() {
        mHandler.post(new Runnable() {

            @Override
            public void run() {
                mCursorView.setVisibility(View.INVISIBLE);
            }
            
        });
    }

    private int calcAxis(int value, boolean isXAxis) {
        int diff = 0;
        if (isXAxis) {
            diff = mCurrentDisplay.getWidth() / 2;
        } else {
            diff = mCurrentDisplay.getHeight() / 2;
        }
        return value - diff;
    }
    
    private void doShowCursor(final int x, final int y, final boolean isDown) {
        Log.d(TAG, "show cursor at " + x + ", " + y + isDown);
        mCursorView.setImageResource(isDown ? R.drawable.cursor_pressed
                : R.drawable.cursor);
        mCursorView.setVisibility(View.VISIBLE);
        mParams.x = calcAxis(x, true);
        mParams.y = calcAxis(y, false);
        try {
            mUpdateLayout.invoke(mWM, mCursorView, mParams);
        } catch (Throwable e) {
            Log.e(TAG, "Fail to get show cursor at " + x + ", " + y + "!!", e);
        }
        // This will remove all callbacks.
        mHandler.removeMessages(0);
        mHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                hideCursor();
            }
        }, CURSOR_DISPLAY_TIMEOUT);
    }

    private void showCursor(final int x, final int y, final boolean isDown) {
        mHandler.post(new Runnable() {

            @Override
            public void run() {
                doShowCursor(x, y, isDown);
            }
        });
    }

    private void startServer() {
        Thread thread = new HolyGrailServerThread();
        thread.start();
    }

    private class HolyGrailServerThread extends Thread {
        int PORT = 9991;
        ServerSocket mServerSocket;
        Socket mAcceptSocket;
        Socket mClientSocket;
        Thread mClientThread;

        public void run() {
            Log.i(TAG, "server thread start.");
            try {
                mServerSocket = new ServerSocket(PORT);
                mServerSocket.setReuseAddress(true);

                while (true) {
                    Log.d(TAG, "waiting...");
                    mAcceptSocket = mServerSocket.accept();
                    Log.d(TAG, "accepted!");

                    if (mClientSocket != null) {
                        Log.d(TAG, "Disconnect already existing connection.");
                        mClientSocket.close();
                    }
                    mClientSocket = mAcceptSocket;
                    mClientThread = new ClientThread();
                    mClientThread.start();
                }
            } catch (IOException e) {
                e.printStackTrace();
            }
        }

        // HIDE
        // SHOW <x> <y> [pressed]
        private class ClientThread extends Thread {
            static final int LENGTH_HEADER_SIZE = 3;
            static final int BUFFER_SIZE = 256;
            InputStreamReader mStreamFromClient;
            OutputStreamWriter mStreamToClient;
            BufferedReader mBufferFromClient;
            BufferedWriter mBufferToClient;

            public void run() {
                Log.d(TAG, "Client thread Start.");
                try {
                    if (mClientSocket == null) {
                        return;
                    }
                    mStreamFromClient = new InputStreamReader(
                            mClientSocket.getInputStream());
                    mStreamToClient = new OutputStreamWriter(
                            mClientSocket.getOutputStream());

                    char[] packetBuffer = new char[BUFFER_SIZE];
                    int receivedCount = 0;
                    String packet = null;

                    while (true) {
                        Log.d(TAG, "loop entry.");
                        mBufferFromClient = new BufferedReader(
                                mStreamFromClient);
                        mBufferToClient = new BufferedWriter(mStreamToClient);

                        receivedCount = mBufferFromClient.read(packetBuffer, 0,
                                LENGTH_HEADER_SIZE);
                        if (receivedCount < 0) {
                            Log.d(TAG,
                                    "Received packet size is -1."
                                            + " Maybe client disconnected unexpectedly.");
                            mClientSocket.close();
                            return;
                        }
                        packet = String.valueOf(packetBuffer, 0, receivedCount);
                        Log.d(TAG, "received : " + packet);
                        
                        int length = 0;
                        try {
                            length = Integer.valueOf(packet);                            
                        } catch (Throwable e) {
                            Log.d(TAG, "Length header is wrong!", e);
                        }
                        
                        receivedCount = mBufferFromClient.read(packetBuffer, 0,
                                length);
                        if (receivedCount < 0) {
                            Log.d(TAG,
                                    "Received packet size is -1."
                                            + " Maybe client disconnected unexpectedly.");
                            mClientSocket.close();
                            return;
                        }
                        packet = String.valueOf(packetBuffer, 0, receivedCount);
                        Log.d(TAG, "received : " + packet);
                        

                        String[] splitted = packet.split(" ");
                        for (int i = 0; i < splitted.length; i++) {
                        }
                        if ("HIDE".equals(splitted[0])) {
                            hideCursor();
                        } else if ("SHOW".equals(splitted[0])) {
                            int x = Integer.valueOf(splitted[1]);
                            int y = Integer.valueOf(splitted[2]);
                            boolean isPressed = splitted.length >= 4
                                    && "pressed".equals(splitted[3]);
                            showCursor(x, y, isPressed);
                        } else {
                            Log.e(TAG, "Invalid packet!" + packet + splitted);
                        }
                    }
                } catch (IOException e) {
                    Log.e(TAG, "IOException while run client thread loop!", e);
                }
            }
        }
    }
}
