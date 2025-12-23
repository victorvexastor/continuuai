use axum::{
    extract::Query,
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::fs;
use walkdir::WalkDir;

const WORKSPACE_DIR: &str = "./workspace";

#[derive(Debug, Serialize)]
pub struct FileNode {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub children: Option<Vec<FileNode>>,
}

#[derive(Debug, Deserialize)]
pub struct PathQuery {
    pub path: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct FileContent {
    pub content: String,
}

pub async fn get_file_tree(Query(params): Query<PathQuery>) -> Result<Json<FileNode>, AppError> {
    let base_path = Path::new(WORKSPACE_DIR);
    let target_path = params.path.as_deref().unwrap_or("");
    let full_path = base_path.join(target_path);

    if !full_path.exists() {
        fs::create_dir_all(&full_path)?;
    }

    let tree = build_tree(&full_path, "")?;
    Ok(Json(tree))
}

fn build_tree(path: &Path, relative_path: &str) -> Result<FileNode, AppError> {
    let name = path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or(WORKSPACE_DIR)
        .to_string();

    if path.is_file() {
        return Ok(FileNode {
            name,
            path: relative_path.to_string(),
            is_dir: false,
            children: None,
        });
    }

    let mut children = Vec::new();
    let entries = fs::read_dir(path)?;

    for entry in entries {
        let entry = entry?;
        let entry_path = entry.path();
        
        // Skip hidden files and .git directory
        if let Some(file_name) = entry_path.file_name().and_then(|n| n.to_str()) {
            if file_name.starts_with('.') {
                continue;
            }
        }

        let child_relative = if relative_path.is_empty() {
            entry.file_name().to_string_lossy().to_string()
        } else {
            format!("{}/{}", relative_path, entry.file_name().to_string_lossy())
        };

        let child_node = build_tree(&entry_path, &child_relative)?;
        children.push(child_node);
    }

    // Sort: directories first, then files, alphabetically
    children.sort_by(|a, b| {
        if a.is_dir == b.is_dir {
            a.name.cmp(&b.name)
        } else if a.is_dir {
            std::cmp::Ordering::Less
        } else {
            std::cmp::Ordering::Greater
        }
    });

    Ok(FileNode {
        name,
        path: relative_path.to_string(),
        is_dir: true,
        children: Some(children),
    })
}

pub async fn get_file_content(Query(params): Query<PathQuery>) -> Result<String, AppError> {
    let path = params.path.ok_or(AppError::BadRequest("Missing path parameter".into()))?;
    let full_path = Path::new(WORKSPACE_DIR).join(&path);

    if !full_path.exists() {
        return Err(AppError::NotFound);
    }

    if !full_path.is_file() {
        return Err(AppError::BadRequest("Path is not a file".into()));
    }

    let content = fs::read_to_string(&full_path)?;
    Ok(content)
}

pub async fn save_file(
    Query(params): Query<PathQuery>,
    content: String,
) -> Result<StatusCode, AppError> {
    let path = params.path.ok_or(AppError::BadRequest("Missing path parameter".into()))?;
    let full_path = Path::new(WORKSPACE_DIR).join(&path);

    // Create parent directories if they don't exist
    if let Some(parent) = full_path.parent() {
        fs::create_dir_all(parent)?;
    }

    fs::write(&full_path, content)?;
    Ok(StatusCode::OK)
}

pub async fn create_file(Query(params): Query<PathQuery>) -> Result<StatusCode, AppError> {
    let path = params.path.ok_or(AppError::BadRequest("Missing path parameter".into()))?;
    let full_path = Path::new(WORKSPACE_DIR).join(&path);

    if full_path.exists() {
        return Err(AppError::BadRequest("File or directory already exists".into()));
    }

    // Check if path ends with / to determine if it's a directory
    if path.ends_with('/') {
        fs::create_dir_all(&full_path)?;
    } else {
        if let Some(parent) = full_path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(&full_path, "")?;
    }

    Ok(StatusCode::CREATED)
}

pub async fn delete_file(Query(params): Query<PathQuery>) -> Result<StatusCode, AppError> {
    let path = params.path.ok_or(AppError::BadRequest("Missing path parameter".into()))?;
    let full_path = Path::new(WORKSPACE_DIR).join(&path);

    if !full_path.exists() {
        return Err(AppError::NotFound);
    }

    if full_path.is_dir() {
        fs::remove_dir_all(&full_path)?;
    } else {
        fs::remove_file(&full_path)?;
    }

    Ok(StatusCode::OK)
}

// Error handling
#[derive(Debug)]
pub enum AppError {
    NotFound,
    BadRequest(String),
    InternalError(String),
}

impl From<std::io::Error> for AppError {
    fn from(err: std::io::Error) -> Self {
        AppError::InternalError(err.to_string())
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            AppError::NotFound => (StatusCode::NOT_FOUND, "Not found".to_string()),
            AppError::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg),
            AppError::InternalError(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg),
        };

        (status, message).into_response()
    }
}
