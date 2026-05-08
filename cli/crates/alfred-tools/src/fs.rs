use std::fs;

use camino::{Utf8Path, Utf8PathBuf};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileEntry {
    pub path: Utf8PathBuf,
    pub is_dir: bool,
}

#[derive(Debug, Default)]
pub struct FsTool;

impl FsTool {
    pub fn read(&self, path: &Utf8Path) -> anyhow::Result<String> {
        Ok(fs::read_to_string(path)?)
    }

    pub fn write(&self, path: &Utf8Path, contents: &str) -> anyhow::Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, contents)?;
        Ok(())
    }

    pub fn list(&self, path: &Utf8Path) -> anyhow::Result<Vec<FileEntry>> {
        let mut entries = Vec::new();
        for entry in fs::read_dir(path)? {
            let entry = entry?;
            let file_type = entry.file_type()?;
            let path = Utf8PathBuf::from_path_buf(entry.path())
                .map_err(|_| anyhow::anyhow!("Non-utf8 path"))?;
            entries.push(FileEntry {
                path,
                is_dir: file_type.is_dir(),
            });
        }
        Ok(entries)
    }
}
