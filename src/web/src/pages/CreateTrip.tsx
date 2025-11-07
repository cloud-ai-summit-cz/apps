import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { tripApiClient } from '../services/tripApiClient';
import { toyApiClient } from '../services/toyApiClient';
import { PlaceStatus } from '../types/trip';
import type { TripCreate, Place } from '../types/trip';
import type { Toy } from '../types/toy';

function CreateTrip() {
  const { toyId } = useParams<{ toyId: string }>();
  const navigate = useNavigate();
  
  const [toy, setToy] = useState<Toy | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form fields
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [locationName, setLocationName] = useState('');
  const [countryCode, setCountryCode] = useState('');
  const [publicTracking, setPublicTracking] = useState(false);
  const [places, setPlaces] = useState<Place[]>([]);

  useEffect(() => {
    if (toyId) {
      loadToy();
    }
  }, [toyId]);

  const loadToy = async () => {
    if (!toyId) return;
    
    try {
      setLoading(true);
      const data = await toyApiClient.getToy(toyId);
      setToy(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load toy');
    } finally {
      setLoading(false);
    }
  };

  const addPlace = () => {
    const newPlace: Place = {
      place_number: places.length + 1,
      name: '',
      status: PlaceStatus.PLANNED,
    };
    setPlaces([...places, newPlace]);
  };

  const updatePlace = (index: number, field: keyof Place, value: string) => {
    const updated = [...places];
    (updated[index] as any)[field] = value;
    setPlaces(updated);
  };

  const removePlace = (index: number) => {
    const updated = places.filter((_, i) => i !== index);
    // Renumber places
    updated.forEach((place, i) => {
      place.place_number = i + 1;
    });
    setPlaces(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!toyId) return;
    
    // Validation
    if (!title.trim()) {
      alert('Please enter a trip title');
      return;
    }
    
    if (!locationName.trim()) {
      alert('Please enter a destination');
      return;
    }
    
    if (!countryCode.trim() || countryCode.length !== 2) {
      alert('Please enter a valid 2-letter country code (e.g., US, GB, JP)');
      return;
    }
    
    // Validate places have names
    for (let i = 0; i < places.length; i++) {
      if (!places[i].name.trim()) {
        alert(`Please enter a name for place ${i + 1}`);
        return;
      }
    }
    
    try {
      setSubmitting(true);
      setError(null);
      
      const tripData: TripCreate = {
        toy_id: toyId,
        title: title.trim(),
        description: description.trim() || undefined,
        location_name: locationName.trim(),
        country_code: countryCode.trim().toUpperCase(),
        public_tracking_enabled: publicTracking,
        places: places.length > 0 ? places : undefined,
      };
      
      const newTrip = await tripApiClient.createTrip(tripData);
      
      // Navigate to the new trip
      navigate(`/trip/${newTrip.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create trip');
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-4rem)]">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  if (error && !toy) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] gap-4">
        <div className="text-red-600">{error}</div>
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
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <button
        onClick={() => navigate(`/toy/${toyId}/trips`)}
        className="text-gray-600 hover:text-gray-900 mb-6 flex items-center gap-2"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to trips
      </button>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">
          Create New Trip for {toy?.name}
        </h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Info */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Trip Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900"
              maxLength={200}
              placeholder="e.g., Summer Adventure in Tokyo"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900 min-h-[100px]"
              maxLength={1000}
              placeholder="Describe this trip..."
            />
            <div className="text-xs text-gray-500 mt-1">
              {description.length}/1000 characters
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Destination *
              </label>
              <input
                type="text"
                value={locationName}
                onChange={(e) => setLocationName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900"
                maxLength={200}
                placeholder="e.g., Tokyo"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Country Code *
              </label>
              <input
                type="text"
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value.toUpperCase())}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900"
                maxLength={2}
                placeholder="e.g., JP"
                required
              />
              <div className="text-xs text-gray-500 mt-1">
                ISO 3166-1 alpha-2 code
              </div>
            </div>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="publicTracking"
              checked={publicTracking}
              onChange={(e) => setPublicTracking(e.target.checked)}
              className="h-4 w-4 text-gray-900 focus:ring-gray-900 border-gray-300 rounded"
            />
            <label htmlFor="publicTracking" className="ml-2 block text-sm text-gray-700">
              Enable public location tracking
            </label>
          </div>

          {/* Places */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="block text-sm font-medium text-gray-700">
                Places to Visit (Optional)
              </label>
              <button
                type="button"
                onClick={addPlace}
                className="text-sm text-gray-900 hover:text-gray-700 flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add Place
              </button>
            </div>

            {places.length === 0 ? (
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center text-gray-500">
                <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <p className="text-sm">No places added yet</p>
                <p className="text-xs mt-1">Add specific landmarks or locations to visit</p>
              </div>
            ) : (
              <div className="space-y-3">
                {places.map((place, index) => (
                  <div key={index} className="flex gap-3 items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-gray-900 text-white rounded-full flex items-center justify-center font-medium text-sm">
                      {place.place_number}
                    </div>
                    
                    <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <input
                        type="text"
                        value={place.name}
                        onChange={(e) => updatePlace(index, 'name', e.target.value)}
                        className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900"
                        placeholder="Place name"
                        maxLength={200}
                        required
                      />
                      
                      <input
                        type="text"
                        value={place.notes || ''}
                        onChange={(e) => updatePlace(index, 'notes', e.target.value)}
                        className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900"
                        placeholder="Notes (optional)"
                        maxLength={1000}
                      />
                    </div>
                    
                    <button
                      type="button"
                      onClick={() => removePlace(index)}
                      className="flex-shrink-0 text-gray-400 hover:text-red-600"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 bg-gray-900 text-white px-6 py-3 rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {submitting ? 'Creating Trip...' : 'Create Trip'}
            </button>
            
            <button
              type="button"
              onClick={() => navigate(`/toy/${toyId}/trips`)}
              disabled={submitting}
              className="px-6 py-3 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreateTrip;
