async function uploadSyllabus(params) {
    const fileInput = document.getElementById("syllabusFile");
    const uploadStatus = document.getElementById("uploadStatus");

    if (!fileInput.files.length){
        uploadStatus.textContent = "Choose a file first";
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file)
    try {
        const res = await fetch("/upload_syllabus",{
        method: "POST",
        body: formData
    });
        const data = await res.json();
        uploadStatus.textContent = data.message || data.error;

    }
    catch(err){
        uploadStatus.textContent = "Failed Upload: " + err.message;
    }
}

async function uploadAssignment(params) {
    const fileInput = document.getElementById("assignmentFile");
    const uploadStatus = document.getElementById("uploadAssignmentStatus");

     if (!fileInput.files.length){
        uploadStatus.textContent = "Choose a file first";
        return;
    }
const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file)

    try {
        const res = await fetch("/uploadAssignment",{
        method: "POST",
        body: formData
    });
        const data = await res.json();
        uploadStatus.textContent = data.message || data.error;

    }
    catch(err){
        uploadStatus.textContent = "Failed Upload: " + err.message;
    }

}