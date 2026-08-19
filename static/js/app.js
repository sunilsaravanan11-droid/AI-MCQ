// app.js - small shared interactivity used across pages

document.addEventListener('DOMContentLoaded', function () {
  var fileInput = document.getElementById('pdf_file');
  var dropzoneText = document.getElementById('dropzone-text');
  var dropzone = document.getElementById('dropzone');
  var uploadForm = document.getElementById('upload-form');
  var uploadBtn = document.getElementById('upload-btn');
  var uploadBtnText = document.getElementById('upload-btn-text');

  document.querySelectorAll('[data-password-toggle]').forEach(function (toggle) {
    var input = document.getElementById(toggle.dataset.passwordToggle);
    if (!input) {
      return;
    }
    toggle.addEventListener('click', function () {
      var isVisible = input.type === 'text';
      input.type = isVisible ? 'password' : 'text';
      toggle.setAttribute('aria-label', isVisible ? 'Show password' : 'Hide password');
      toggle.setAttribute('title', isVisible ? 'Show password' : 'Hide password');
    });
  });

  if (fileInput && dropzoneText) {
    fileInput.addEventListener('change', function () {
      if (fileInput.files && fileInput.files.length > 0) {
        dropzoneText.textContent = fileInput.files[0].name;
      } else {
        dropzoneText.textContent = 'Click to choose a PDF, or drag it here';
      }
    });
  }

  if (dropzone) {
    ['dragover', 'dragenter'].forEach(function (evt) {
      dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--flame-1)';
      });
    });
    ['dragleave', 'drop'].forEach(function (evt) {
      dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        dropzone.style.borderColor = '';
      });
    });
    dropzone.addEventListener('drop', function (e) {
      var files = e.dataTransfer.files;
      if (files && files.length > 0 && fileInput) {
        fileInput.files = files;
        dropzoneText.textContent = files[0].name;
      }
    });
  }

  if (uploadForm && uploadBtn && uploadBtnText) {
    uploadForm.addEventListener('submit', function () {
      if (!fileInput.files || fileInput.files.length === 0) {
        return; // let native validation handle it
      }
      uploadBtn.disabled = true;
      uploadBtnText.textContent = 'Reading PDF & detecting topics...';
      uploadBtn.classList.add('btn-loading');
    });
  }
});
