use axum::{
    extract::Query,
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use git2::{Repository, StatusOptions, DiffOptions, BranchType, Signature, Oid};
use serde::{Deserialize, Serialize};
use std::path::Path;

const WORKSPACE_DIR: &str = "./workspace";

#[derive(Debug, Serialize)]
pub struct GitStatus {
    pub branch: String,
    pub modified: Vec<String>,
    pub created: Vec<String>,
    pub deleted: Vec<String>,
    pub staged: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct GitBranch {
    pub name: String,
    pub is_current: bool,
}

#[derive(Debug, Serialize)]
pub struct GitCommit {
    pub id: String,
    pub author: String,
    pub message: String,
    pub timestamp: i64,
}

#[derive(Debug, Serialize)]
pub struct GitDiff {
    pub path: String,
    pub diff: String,
}

#[derive(Debug, Deserialize)]
pub struct CommitRequest {
    pub message: String,
}

#[derive(Debug, Deserialize)]
pub struct CheckoutRequest {
    pub branch: String,
}

#[derive(Debug, Deserialize)]
pub struct DiffQuery {
    pub file: Option<String>,
}

pub async fn get_status() -> Result<Json<GitStatus>, GitError> {
    let repo = Repository::open(WORKSPACE_DIR)?;
    
    let head = repo.head()?;
    let branch = head
        .shorthand()
        .unwrap_or("HEAD")
        .to_string();

    let mut opts = StatusOptions::new();
    opts.include_untracked(true);
    
    let statuses = repo.statuses(Some(&mut opts))?;

    let mut modified = Vec::new();
    let mut created = Vec::new();
    let mut deleted = Vec::new();
    let mut staged = Vec::new();

    for entry in statuses.iter() {
        let path = entry.path().unwrap_or("").to_string();
        let status = entry.status();

        if status.is_index_new() || status.is_index_modified() || status.is_index_deleted() {
            staged.push(path.clone());
        }

        if status.is_wt_modified() || status.is_index_modified() {
            modified.push(path.clone());
        }
        
        if status.is_wt_new() || status.is_index_new() {
            created.push(path.clone());
        }
        
        if status.is_wt_deleted() || status.is_index_deleted() {
            deleted.push(path);
        }
    }

    Ok(Json(GitStatus {
        branch,
        modified,
        created,
        deleted,
        staged,
    }))
}

pub async fn get_branches() -> Result<Json<Vec<GitBranch>>, GitError> {
    let repo = Repository::open(WORKSPACE_DIR)?;
    let mut branches = Vec::new();

    let current_branch = repo.head()?.shorthand().unwrap_or("").to_string();

    for branch in repo.branches(Some(BranchType::Local))? {
        let (branch, _) = branch?;
        if let Some(name) = branch.name()? {
            branches.push(GitBranch {
                name: name.to_string(),
                is_current: name == current_branch,
            });
        }
    }

    Ok(Json(branches))
}

pub async fn commit(Json(req): Json<CommitRequest>) -> Result<StatusCode, GitError> {
    let repo = Repository::open(WORKSPACE_DIR)?;
    
    // Get the default signature
    let signature = repo.signature()?;
    
    // Get the index and write tree
    let mut index = repo.index()?;
    
    // Add all changes
    index.add_all(["*"].iter(), git2::IndexAddOption::DEFAULT, None)?;
    index.write()?;
    
    let tree_id = index.write_tree()?;
    let tree = repo.find_tree(tree_id)?;
    
    // Get parent commit
    let parent_commit = repo.head()?.peel_to_commit()?;
    
    // Create the commit
    repo.commit(
        Some("HEAD"),
        &signature,
        &signature,
        &req.message,
        &tree,
        &[&parent_commit],
    )?;

    Ok(StatusCode::OK)
}

pub async fn checkout_branch(Json(req): Json<CheckoutRequest>) -> Result<StatusCode, GitError> {
    let repo = Repository::open(WORKSPACE_DIR)?;
    
    // Find the branch
    let branch = repo.find_branch(&req.branch, BranchType::Local)?;
    let commit = branch.get().peel_to_commit()?;
    
    // Set HEAD to the branch
    repo.set_head(&format!("refs/heads/{}", req.branch))?;
    
    // Checkout the tree
    repo.checkout_tree(commit.as_object(), None)?;

    Ok(StatusCode::OK)
}

pub async fn get_diff(Query(params): Query<DiffQuery>) -> Result<Json<Vec<GitDiff>>, GitError> {
    let repo = Repository::open(WORKSPACE_DIR)?;
    
    let head = repo.head()?.peel_to_tree()?;
    let mut diff_opts = DiffOptions::new();
    
    if let Some(file_path) = params.file {
        diff_opts.pathspec(&file_path);
    }
    
    let diff = repo.diff_tree_to_workdir(Some(&head), Some(&mut diff_opts))?;
    
    let mut diffs = Vec::new();
    
    diff.print(git2::DiffFormat::Patch, |delta, _hunk, line| {
        if let Some(path) = delta.new_file().path() {
            let path_str = path.to_string_lossy().to_string();
            let line_content = String::from_utf8_lossy(line.content()).to_string();
            
            diffs.push(GitDiff {
                path: path_str,
                diff: line_content,
            });
        }
        true
    })?;

    Ok(Json(diffs))
}

pub async fn get_log() -> Result<Json<Vec<GitCommit>>, GitError> {
    let repo = Repository::open(WORKSPACE_DIR)?;
    let mut revwalk = repo.revwalk()?;
    
    revwalk.push_head()?;
    revwalk.set_sorting(git2::Sort::TIME)?;
    
    let mut commits = Vec::new();
    
    for oid in revwalk.take(50) {
        let oid = oid?;
        let commit = repo.find_commit(oid)?;
        
        commits.push(GitCommit {
            id: oid.to_string(),
            author: commit.author().name().unwrap_or("Unknown").to_string(),
            message: commit.message().unwrap_or("").to_string(),
            timestamp: commit.time().seconds(),
        });
    }

    Ok(Json(commits))
}

// Error handling
#[derive(Debug)]
pub enum GitError {
    Git(git2::Error),
    NotFound,
}

impl From<git2::Error> for GitError {
    fn from(err: git2::Error) -> Self {
        GitError::Git(err)
    }
}

impl IntoResponse for GitError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            GitError::Git(err) => (StatusCode::INTERNAL_SERVER_ERROR, err.to_string()),
            GitError::NotFound => (StatusCode::NOT_FOUND, "Not found".to_string()),
        };

        (status, message).into_response()
    }
}
