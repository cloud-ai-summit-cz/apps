import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMsal } from '@azure/msal-react';
import { toyApiClient } from '../services/toyApiClient';
import type { Toy } from '../types/toy';

function ToyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { accounts } = useMsal();
  const userOid = accounts[0]?.idTokenClaims?.oid as string | undefined;
  
  const [toy, setToy] = useState<Toy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [loadingAvatar, setLoadingAvatar] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isOwner = toy && toy.owner_oid === userOid;

  useEffect(() => {
    if (id) {
      loadToy();
    }
  }, [id]);

  useEffect(() => {
    // Load avatar when toy changes
    if (toy?.avatar_blob_name && id) {
      loadAvatar();
    }
    
    // Cleanup blob URL on unmount or when toy changes
    return () => {
      if (avatarUrl) {
        URL.revokeObjectURL(avatarUrl);
      }
    };
  }, [toy?.avatar_blob_name, id]);

  const loadToy = async () => {
    if (!id) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await toyApiClient.getToy(id);
      setToy(data);
      setEditName(data.name);
      setEditDescription(data.description || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load toy');
    } finally {
      setLoading(false);
    }
  };

  const loadAvatar = async () => {
    if (!id || loadingAvatar) return;
    
    try {
      setLoadingAvatar(true);
      const blobUrl = await toyApiClient.getAvatarBlob(id);
      setAvatarUrl(blobUrl);
    } catch (err) {
      console.error('Failed to load avatar:', err);
    } finally {
      setLoadingAvatar(false);
    }
  };

  const handleSave = async () => {
    if (!id || !toy) return;
    
    try {
      setIsSaving(true);
      await toyApiClient.updateToy(id, {
        name: editName,
        description: editDescription || undefined,
      });
      await loadToy();
      setIsEditing(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update toy');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!id || !confirm('Are you sure you want to delete this toy?')) return;
    
    try {
      setIsDeleting(true);
      await toyApiClient.deleteToy(id);
      navigate('/');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete toy');
      setIsDeleting(false);
    }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!id || !e.target.files || e.target.files.length === 0) return;
    
    const file = e.target.files[0];
    
    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('File size must be less than 5MB');
      return;
    }
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('File must be an image');
      return;
    }
    
    try {
      setUploadingAvatar(true);
      await toyApiClient.uploadAvatar(id, file);
      // Revoke old blob URL
      if (avatarUrl) {
        URL.revokeObjectURL(avatarUrl);
        setAvatarUrl(null);
      }
      await loadToy();
      // Avatar will be reloaded by the useEffect that watches toy.avatar_blob_name
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to upload avatar');
    } finally {
      setUploadingAvatar(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteAvatar = async () => {
    if (!id || !confirm('Are you sure you want to delete the avatar?')) return;
    
    try {
      // Revoke old blob URL
      if (avatarUrl) {
        URL.revokeObjectURL(avatarUrl);
        setAvatarUrl(null);
      }
      await toyApiClient.deleteAvatar(id);
      await loadToy();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete avatar');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-4rem)]">
        <div className="text-gray-600">Loading toy...</div>
      </div>
    );
  }

  if (error || !toy) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] gap-4">
        <div className="text-red-600">{error || 'Toy not found'}</div>
        <button
          onClick={() => navigate('/')}
          className="text-blue-600 hover:text-blue-700"
        >
          Back to catalog
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <button
        onClick={() => navigate('/')}
        className="text-gray-600 hover:text-gray-900 mb-6 flex items-center gap-2"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to catalog
      </button>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6">
          <div className="flex flex-col md:flex-row gap-8">
            {/* Avatar Section */}
            <div className="flex-shrink-0">
              <div className="w-64 h-64 bg-gray-100 rounded-lg overflow-hidden">
                {loadingAvatar ? (
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="text-gray-400">Loading avatar...</div>
                  </div>
                ) : avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt={toy.name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.currentTarget.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="256" height="256"%3E%3Crect width="256" height="256" fill="%23e5e7eb"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="96" fill="%239ca3af"%3E' + toy.name.charAt(0).toUpperCase() + '%3C/text%3E%3C/svg%3E';
                    }}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <span className="text-8xl text-gray-400 font-medium">
                      {toy.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                )}
              </div>
              
              {isOwner && (
                <div className="mt-4 flex gap-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleAvatarUpload}
                    className="hidden"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadingAvatar}
                    className="flex-1 px-4 py-2 bg-gray-900 text-white rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                  >
                    {uploadingAvatar ? 'Uploading...' : 'Upload Avatar'}
                  </button>
                  {toy.avatar_blob_name && (
                    <button
                      onClick={handleDeleteAvatar}
                      className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 text-sm"
                    >
                      Delete
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Info Section */}
            <div className="flex-1 min-w-0">
              {isEditing ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Name
                    </label>
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900"
                      maxLength={100}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Description
                    </label>
                    <textarea
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900 min-h-[120px]"
                      maxLength={500}
                    />
                    <div className="text-xs text-gray-500 mt-1">
                      {editDescription.length}/500 characters
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={handleSave}
                      disabled={isSaving || !editName.trim()}
                      className="px-4 py-2 bg-gray-900 text-white rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSaving ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => {
                        setIsEditing(false);
                        setEditName(toy.name);
                        setEditDescription(toy.description || '');
                      }}
                      disabled={isSaving}
                      className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <h1 className="text-3xl font-bold text-gray-900">{toy.name}</h1>
                    {isOwner && (
                      <span className="inline-block mt-2 bg-gray-900 text-white text-xs px-2 py-1 rounded-full font-medium">
                        My Toy
                      </span>
                    )}
                  </div>
                  
                  <div>
                    <h2 className="text-sm font-medium text-gray-500 mb-1">Description</h2>
                    <p className="text-gray-700 whitespace-pre-wrap">
                      {toy.description || 'No description provided.'}
                    </p>
                  </div>

                  <div className="pt-4 text-xs text-gray-500 space-y-1">
                    <div>Created: {new Date(toy.created_at).toLocaleString()}</div>
                    <div>Updated: {new Date(toy.updated_at).toLocaleString()}</div>
                  </div>

                  {isOwner && (
                    <div className="pt-4 flex gap-2">
                      <button
                        onClick={() => setIsEditing(true)}
                        className="px-4 py-2 bg-gray-900 text-white rounded-md hover:bg-gray-800"
                      >
                        Edit
                      </button>
                      <button
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isDeleting ? 'Deleting...' : 'Delete Toy'}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ToyDetail;
