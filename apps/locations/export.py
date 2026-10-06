import pandas as pd
from django.http import HttpResponse


def export_locations_csv(locations):
    data = []

    for location in locations:
        data.append(
            {
                "id": location.id,
                "name": location.name,
                "description": location.description,
                "category": location.category.name,
                "address": location.address,
                "latitude": float(location.latitude),
                "longitude": float(location.longitude),
                "author": location.author.username,
                "rating": location.rating or 0,
                "reviews_count": location.reviews_count,
                "created_at": location.created_at.isoformat(),
                "updated_at": location.updated_at.isoformat(),
                "popularity": location.popularity,
            }
        )

    dataframe = pd.DataFrame(data)

    response = HttpResponse(
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = (
        'attachment; filename="locations.csv"'
    )

    dataframe.to_csv(response, index=False)

    return response