use axum::{
    extract::ws::{Message, WebSocket, WebSocketUpgrade},
    response::Response,
};
use futures_util::{StreamExt, SinkExt};
use portable_pty::{native_pty_system, CommandBuilder, PtySize};
use std::io::{Read, Write};
use std::sync::Arc;
use tokio::sync::Mutex;

pub async fn terminal_handler(ws: WebSocketUpgrade) -> Response {
    ws.on_upgrade(handle_socket)
}

async fn handle_socket(socket: WebSocket) {
    let (mut sender, mut receiver) = socket.split();
    
    // Create a PTY
    let pty_system = native_pty_system();
    let pair = match pty_system.openpty(PtySize {
        rows: 24,
        cols: 80,
        pixel_width: 0,
        pixel_height: 0,
    }) {
        Ok(pair) => pair,
        Err(e) => {
            tracing::error!("Failed to create PTY: {}", e);
            return;
        }
    };

    // Spawn a shell
    let mut cmd = CommandBuilder::new("bash");
    cmd.cwd("./workspace");
    
    let mut child = match pair.slave.spawn_command(cmd) {
        Ok(child) => child,
        Err(e) => {
            tracing::error!("Failed to spawn shell: {}", e);
            return;
        }
    };

    let mut reader = pair.master.try_clone_reader().unwrap();
    let mut writer = pair.master.take_writer().unwrap();

    // Task to read from PTY and send to WebSocket
    let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel();
    
    tokio::spawn(async move {
        let mut buf = [0u8; 8192];
        loop {
            match reader.read(&mut buf) {
                Ok(n) if n > 0 => {
                    if tx.send(buf[..n].to_vec()).is_err() {
                        break;
                    }
                }
                _ => break,
            }
        }
    });

    // Task to send PTY output to WebSocket
    let send_task = tokio::spawn(async move {
        while let Some(data) = rx.recv().await {
            if sender
                .send(Message::Binary(data))
                .await
                .is_err()
            {
                break;
            }
        }
    });

    // Task to receive from WebSocket and write to PTY
    let write_task = tokio::spawn(async move {
        while let Some(Ok(msg)) = receiver.next().await {
            match msg {
                Message::Text(text) => {
                    if writer.write_all(text.as_bytes()).is_err() {
                        break;
                    }
                }
                Message::Binary(data) => {
                    if writer.write_all(&data).is_err() {
                        break;
                    }
                }
                Message::Close(_) => break,
                _ => {}
            }
        }
    });

    // Wait for either task to complete
    tokio::select! {
        _ = send_task => {}
        _ = write_task => {}
    }

    // Cleanup
    let _ = child.kill();
}
