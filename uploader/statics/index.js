function goToUpload(event) {
  const input = document.getElementById("token");
  window.location = `/upload?token=${input.value}`;
  event.preventDefault();
}

function goToUploadWith(token) {
    window.location = `/upload?token=${token}`;
}

function copyFunction(token) {
  navigator.clipboard.writeText(token).then(
    function () {}, // success
    function () {}  // error
  );
}

window.goToUpload = goToUpload;
window.goToUploadWith = goToUploadWith;
window.copyFunction = copyFunction;
