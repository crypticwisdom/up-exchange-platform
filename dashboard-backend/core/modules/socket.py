# from socketio import AsyncServer
# from socketio.contrib.django import DjangoNamespace
# from rest_framework.views import APIView
# from rest_framework.response import Response
#
# # django-socketio django-channels
#
# # create a socketio server
# sio = AsyncServer(async_mode='asgi')
# namespace = DjangoNamespace('/api/socketio')
#
# # create a websocket view
# class MyWebSocket(APIView):
#     async def get(self, request):
#         return await sio.handle_request(request.environ, request)
#
# # define an event handler
# @sio.event(namespace='/api/socketio')
# async def my_event(sid, data):
#     print('received data:', data)
#     await sio.emit('my_response', {'data': data}, room=sid)
#
# # define a channel
# @sio.on('subscribe', namespace='/api/socketio')
# async def subscribe(sid, channel):
#     await sio.enter_room(sid, channel)
#
# # integrate the WebSocket view into your DRF views
# urlpatterns = [
#     path('api/socketio/', MyWebSocket.as_view()),
#     # other views...
# ]