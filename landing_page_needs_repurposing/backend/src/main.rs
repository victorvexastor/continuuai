use axum::{
    extract::Query,
    http::{StatusCode, header},
    response::{IntoResponse, Response},
    routing::{get, post, put, delete},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod files;
mod git;
mod terminal;

#[tokio::main]
async fn main() {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "ide_backend=debug,tower_http=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Build the application router
    let app = Router::new()
        // Health check
        .route("/health", get(health_check))
        // File operations
        .route("/api/files/tree", get(files::get_file_tree))
        .route("/api/files/content", get(files::get_file_content))
        .route("/api/files/content", put(files::save_file))
        .route("/api/files/create", post(files::create_file))
        .route("/api/files/delete", delete(files::delete_file))
        // Git operations
        .route("/api/git/status", get(git::get_status))
        .route("/api/git/branches", get(git::get_branches))
        .route("/api/git/commit", post(git::commit))
        .route("/api/git/checkout", post(git::checkout_branch))
        .route("/api/git/diff", get(git::get_diff))
        .route("/api/git/log", get(git::get_log))
        // Terminal WebSocket
        .route("/api/terminal", get(terminal::terminal_handler))
        // CORS middleware
        .layer(
            CorsLayer::new()
                .allow_origin(Any)
                .allow_methods(Any)
                .allow_headers(Any),
        )
        // Logging middleware
        .layer(TraceLayer::new_for_http());

    // Start server
    let addr = SocketAddr::from(([127, 0, 0, 1], 3002));
    tracing::info!("🚀 IDE Backend listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn health_check() -> &'static str {
    "OK"
}
