package wisdomUtils

// ArrayContains checks if an array contains the specified value by iterating
// over the array and comparing the value against each member of the array.
// The array and value need to be of the same type for this function to work
func ArrayContains[T comparable](a []T, v T) bool {
	for _, item := range a {
		if item == v {
			return true
		}
	}
	return false
}

// MapHasKey uses the ok idiom to check if the map contains the key and returns the result
func MapHasKey[K comparable, V any](m map[K]V, key K) bool {
	_, keyAvailable := m[key]
	return keyAvailable
}
