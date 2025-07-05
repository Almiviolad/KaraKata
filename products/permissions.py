from rest_framework import permissions as permssions


class IsVendorUser(permssions.BasePermission):
    """ checks if user is auheticated and a vendor"""
    
    def has_permission(self, request, view):
        """checks if user is authenticated and a vendor"""
        return request.user and request.user.is_authenticated and request.user.role == 'vendor'
    
    def has_object_permission(self, request, view, obj):
        """checks if user is the vendor of the product"""
        return request.user == obj.vendor