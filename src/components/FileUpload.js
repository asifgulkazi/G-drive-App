import React, { useState } from 'react';
import { Button, Modal, makeStyles, Input } from '@material-ui/core';
import { storage, db } from '../../firebase';
import firebase from 'firebase';

// Styling for the Modal using Material-UI
const useStyles = makeStyles((theme) => ({
    paper: {
        position: 'absolute',
        width: 400,
        backgroundColor: theme.palette.background.paper,
        border: '2px solid #000',
        boxShadow: theme.shadows[5],
        padding: theme.spacing(2, 4, 3),
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        borderRadius: '8px',
        outline: 'none',
    },
    uploadSection: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '20px',
        marginTop: '20px',
    },
    uploadButton: {
        backgroundColor: '#4285F4',
        color: 'white',
        '&:hover': {
            backgroundColor: '#357ae8',
        },
    },
    input: {
        display: 'none',
    },
}));

// The main FileUpload component
const FileUpload = ({ open, handleClose }) => {
    const classes = useStyles();

    const [files, setFiles] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);

    // Handles file selection from the input
    const handleFileChange = (e) => {
        // Convert FileList object to an array
        const selectedFiles = Array.from(e.target.files);
        if (selectedFiles.length > 0) {
            setFiles(selectedFiles);
        }
    };

    // Handles the entire upload process
    const handleUpload = () => {
        if (files.length === 0) {
            // In a real app, you'd use a nicer notification than alert()
            console.warn("Please select files to upload first!");
            return;
        }

        setUploading(true);
        setProgress(0);

        // We use Promise.all to wait for all file uploads to complete
        const uploadPromises = files.map(file => {
            return new Promise((resolve, reject) => {
                const uploadTask = storage.ref(`files/${file.name}`).put(file);

                uploadTask.on(
                    'state_changed',
                    (snapshot) => {
                        // Calculate progress for the current file
                        const currentProgress = Math.round(
                            (snapshot.bytesTransferred / snapshot.totalBytes) * 100
                        );
                        // Note: For multiple files, you might want a more complex progress UI.
                        // Here we just show the progress of one of the files.
                        setProgress(currentProgress);
                    },
                    (error) => {
                        console.error("Upload Error:", error);
                        reject(error); // Reject the promise on error
                    },
                    () => {
                        // On successful upload, get the download URL
                        storage
                            .ref('files')
                            .child(file.name)
                            .getDownloadURL()
                            .then((url) => {
                                // Add file metadata to Firestore database
                                db.collection('myFiles').add({
                                    timestamp: firebase.firestore.FieldValue.serverTimestamp(),
                                    caption: file.name,
                                    fileUrl: url,
                                    size: file.size,
                                });
                                console.log(`${file.name} uploaded successfully.`);
                                resolve(); // Resolve the promise on success
                            })
                            .catch(reject); // Reject if getting URL fails
                    }
                );
            });
        });

        // After all uploads are done
        Promise.all(uploadPromises)
            .then(() => {
                setUploading(false);
                setFiles([]);
                setProgress(0);
                handleClose(); // Close the modal
                console.log("All files uploaded successfully!");
            })
            .catch((error) => {
                setUploading(false);
                console.error(`An error occurred during upload: ${error.message}`);
            });
    };

    return (
        <Modal open={open} onClose={handleClose}>
            <div className={classes.paper}>
                <h2>Upload Files/Folders</h2>
                <div className={classes.uploadSection}>
                    {/* File Input */}
                    <label htmlFor="file-input">
                        <Input
                            id="file-input"
                            type="file"
                            onChange={handleFileChange}
                            className={classes.input}
                            inputProps={{ multiple: true }} // Allow multiple files
                        />
                        <Button variant="outlined" component="span">
                            Choose Files
                        </Button>
                    </label>

                    {/* Folder Input - uses the same file input but with a special property */}
                    <label htmlFor="folder-input">
                        <Input
                            id="folder-input"
                            type="file"
                            onChange={handleFileChange}
                            className={classes.input}
                            inputProps={{ webkitdirectory: "true", directory: "true", multiple: true }}
                        />
                        <Button variant="outlined" component="span">
                            Choose a Folder
                        </Button>
                    </label>

                    {/* Display selected file names */}
                    {files.length > 0 && (
                        <div>
                            <p>Selected:</p>
                            <ul style={{ listStyle: 'none', padding: 0, maxHeight: '100px', overflowY: 'auto' }}>
                                {files.map((file, index) => (
                                    <li key={index}>{file.name}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Upload Button and Progress */}
                    {uploading ? (
                        <p>Uploading... {progress}%</p>
                    ) : (
                        <Button onClick={handleUpload} className={classes.uploadButton} disabled={files.length === 0}>
                            Upload
                        </Button>
                    )}
                </div>
            </div>
        </Modal>
    );
};

export default FileUpload;

