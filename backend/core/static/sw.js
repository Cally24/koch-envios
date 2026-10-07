self.addEventListener("push", function (event) {

    if (!event.data) {
        return;
    }

    const datos = event.data.json();

    const titulo = datos.titulo || "KOCH ENVÍOS";

    const opciones = {
        body: datos.mensaje || "Tienes una nueva notificación.",
        icon: "/logo.png",
        badge: "/logo.png",
        data: {
            url: datos.url || "/operaciones/",
        },
        requireInteraction: true,
    };

    event.waitUntil(
        self.registration.showNotification(
            titulo,
            opciones
        )
    );
});


self.addEventListener("notificationclick", function (event) {

    event.notification.close();

    const url = event.notification.data.url;

    event.waitUntil(
        clients.matchAll({
            type: "window",
            includeUncontrolled: true,
        }).then(function (ventanas) {

            for (const ventana of ventanas) {

                if (ventana.url.includes("/operaciones/")) {
                    ventana.focus();

                    if (url) {
                        ventana.navigate(url);
                    }

                    return;
                }
            }

            return clients.openWindow(url);
        })
    );
});