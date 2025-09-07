"use client";
import { useState, useRef, FormEvent, ChangeEvent } from "react";

const API_BASE_URL = "http://localhost:8000"; // Make sure this matches your FastAPI server's URL

// Define the type for the validation result from the backend
interface ValidationResult {
  classification: string;
  details: Record<string, any>;
  metadata_flags: boolean;
  logo_verified: boolean;
  template_ok: boolean;
}

const Uploader = () => {
  const [file, setFile] = useState<File | null>(null);
  const [validationResult, setValidationResult] =
    useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] || null;
    setFile(selectedFile);
    setValidationResult(null);
    setError(null);
  };

  const handleUpload = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a file to upload.");
      return;
    }

    setLoading(true);
    setError(null);
    setValidationResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: ValidationResult = await response.json();
      setValidationResult(data);
    } catch (e: any) {
      console.error("Upload failed:", e);
      setError(
        "An error occurred during the upload process. Please try again."
      );
    } finally {
      setLoading(false);
      // Optional: Clear the file input after upload
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setFile(null);
    }
  };

  return (
    <div className="min-h-screen w-screen flex items-center justify-center bg-gray-100 p-4">
      <div className="w-full max-w-2xl p-8 bg-white rounded-lg shadow-xl flex flex-col">
        <h1 className="text-3xl font-bold text-center mb-6 text-gray-800">
          Authenticity Validator
        </h1>

        <form
          onSubmit={handleUpload}
          className="flex flex-col items-center space-y-4 w-full"
        >
          <label className="w-full">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded-full file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-50 file:text-blue-700
            hover:file:bg-blue-100"
            />
          </label>
          <button
            type="submit"
            disabled={loading || !file}
            className={`w-full px-6 py-3 rounded-lg font-semibold transition-colors duration-200
          ${
            loading || !file
              ? "bg-gray-300 text-gray-500 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
          >
            {loading ? "Validating..." : "Upload and Validate"}
          </button>
        </form>

        {error && (
          <div
            className="mt-4 p-4 text-sm text-red-700 bg-red-100 rounded-lg break-words"
            role="alert"
          >
            {error}
          </div>
        )}

        {validationResult && (
          <div className="mt-6 p-6 bg-green-50 rounded-lg shadow-inner border-t-4 border-green-500 w-full overflow-x-auto">
            <h2 className="text-2xl font-semibold mb-3 text-green-800">
              Validation Result
            </h2>
            <div className="space-y-2 text-gray-700">
              <p>
                <strong>Classification:</strong>{" "}
                <span className="font-medium">
                  {validationResult.classification}
                </span>
              </p>
              <p>
                <strong>Details:</strong>{" "}
                <pre className="font-mono text-xs whitespace-pre-wrap break-words">
                  {JSON.stringify(validationResult.details, null, 2)}
                </pre>
              </p>
              <p>
                <strong>Metadata Flags:</strong>{" "}
                <span className="font-medium">
                  {validationResult.metadata_flags ? "OK" : "Suspicious"}
                </span>
              </p>
              <p>
                <strong>Logo Verified:</strong>{" "}
                <span className="font-medium">
                  {validationResult.logo_verified ? "Yes" : "No"}
                </span>
              </p>
              <p>
                <strong>Template OK:</strong>{" "}
                <span className="font-medium">
                  {validationResult.template_ok ? "Yes" : "No"}
                </span>
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Uploader;
